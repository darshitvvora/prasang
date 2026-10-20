// Portfolio media manager: upload photos/videos via presigned URLs, add
// YouTube/Instagram links, delete items. Quota comes from the API.
import { useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { PlayCircle, Trash2, Upload } from 'lucide-react';
import { createMedia, deleteMedia, requestUploadUrl, uploadToUrl } from '../api/endpoints';
import { keys, useMyMedia } from '../api/queries';
import { InlineError } from './QueryState';
import { linkKind } from './embed';
import { canUseHd, deletionNote, quotaSummary, uploadProblem } from './mediaLimits';

export default function MediaUploader() {
  const qc = useQueryClient();
  const media = useMyMedia();
  const fileInput = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [linkUrl, setLinkUrl] = useState('');
  const [hd, setHd] = useState(false);

  const refresh = () => {
    qc.invalidateQueries({ queryKey: keys.myMedia });
    qc.invalidateQueries({ queryKey: keys.myArtist });
  };

  async function run(task: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await task();
      refresh();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  function handleFiles(files: FileList | null) {
    if (!files?.length) return;
    run(async () => {
      for (const file of Array.from(files)) {
        const kind = file.type.startsWith('video/') ? 'video' : 'image';
        const asHd = kind === 'video' && hd;
        const problem = uploadProblem(file, kind, asHd);
        if (problem) throw new Error(problem);
        const target = await requestUploadUrl({ kind, contentType: file.type || 'application/octet-stream', sizeBytes: file.size, hd: asHd });
        await uploadToUrl(target, file);
        await createMedia({ kind, storageKey: target.storageKey });
      }
    });
  }

  function handleAddLink(e: React.FormEvent) {
    e.preventDefault();
    const url = linkUrl.trim();
    const kind = linkKind(url);
    if (!kind) {
      setError(new Error('Paste a YouTube, Instagram or Facebook link'));
      return;
    }
    run(async () => {
      await createMedia({ kind, url });
      setLinkUrl('');
    });
  }

  const quota = media.data?.quota;
  return (
    <div className="ob-field">
      <label>Upload portfolio media</label>
      <button type="button" className="ob-upload-box tall" onClick={() => fileInput.current?.click()} disabled={busy}>
        <Upload size={28} />
        <span>{busy ? 'Uploading…' : 'Upload photos & videos of your performances'}</span>
        {quota && <span className="ob-hint">{quotaSummary(quota)} · videos up to 40 MB</span>}
      </button>
      {quota && quota.hdVideos.limit !== 0 && (
        <label className="ob-hd-toggle">
          <input type="checkbox" checked={hd && canUseHd(quota)} disabled={!canUseHd(quota)} onChange={(e) => setHd(e.target.checked)} />
          Upload the next video in HD (up to 200 MB){canUseHd(quota) ? '' : ' — HD slots used'}
        </label>
      )}
      <input ref={fileInput} type="file" accept="image/*,video/*" multiple hidden onChange={(e) => { handleFiles(e.target.files); e.target.value = ''; }} />

      <form className="ob-link-row" onSubmit={handleAddLink}>
        <input className="ob-input" placeholder="Or paste a YouTube, Instagram or Facebook post link" value={linkUrl} onChange={(e) => setLinkUrl(e.target.value)} />
        <button type="submit" className="ob-back-btn" disabled={busy || !linkUrl.trim()}>Add</button>
      </form>

      <InlineError error={error} />

      {media.data && media.data.items.length > 0 && (
        <div className="ob-media-grid">
          {media.data.items.map((m) => (
            <div key={m.id} className="ob-media-item">
              {m.kind === 'image' ? <img src={m.url} alt={m.caption ?? ''} /> : (
                <div className="ob-media-link"><PlayCircle size={22} /> {m.kind === 'youtube' ? 'YouTube' : m.kind === 'instagram' ? 'Instagram' : m.kind === 'facebook' ? 'Facebook' : 'Video'}</div>
              )}
              {m.isHd && <span className="ob-media-badge">HD</span>}
              {deletionNote(m.deleteAfter) && <span className="ob-media-warning">{deletionNote(m.deleteAfter)}</span>}
              <button type="button" className="ob-media-delete" aria-label="Delete" disabled={busy}
                onClick={() => run(() => deleteMedia(m.id))}>
                <Trash2 size={14} />
              </button>
            </div>
          ))}
        </div>
      )}
      {media.data && media.data.items.length === 0 && <span className="ob-hint">No media yet.</span>}
    </div>
  );
}
