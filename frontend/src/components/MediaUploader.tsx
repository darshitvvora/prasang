// Portfolio media manager: upload photos/videos via presigned URLs, add
// YouTube/Instagram links, delete items. Quota comes from the API.
import { useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { PlayCircle, Trash2, Upload } from 'lucide-react';
import { createMedia, deleteMedia, requestUploadUrl, uploadToUrl } from '../api/endpoints';
import { keys, useMyMedia } from '../api/queries';
import { InlineError } from './QueryState';

const MAX_IMAGE_BYTES = 10 * 1024 * 1024;
const MAX_VIDEO_BYTES = 100 * 1024 * 1024;
const limitText = (used: number, limit: number) => (limit < 0 ? `${used} (unlimited)` : `${used}/${limit}`);

export default function MediaUploader() {
  const qc = useQueryClient();
  const media = useMyMedia();
  const fileInput = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [linkUrl, setLinkUrl] = useState('');

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
        if (file.size > (kind === 'video' ? MAX_VIDEO_BYTES : MAX_IMAGE_BYTES)) {
          throw new Error(`${file.name} is too large (max ${kind === 'video' ? '100' : '10'} MB)`);
        }
        const target = await requestUploadUrl({ kind, contentType: file.type || 'application/octet-stream', sizeBytes: file.size });
        await uploadToUrl(target, file);
        await createMedia({ kind, storageKey: target.storageKey });
      }
    });
  }

  function handleAddLink(e: React.FormEvent) {
    e.preventDefault();
    const url = linkUrl.trim();
    const kind = /youtu\.?be/.test(url) ? 'youtube' : /instagram\.com/.test(url) ? 'instagram' : null;
    if (!kind) {
      setError(new Error('Paste a YouTube or Instagram link'));
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
        {quota && (
          <span className="ob-hint">Photos {limitText(quota.images.used, quota.images.limit)} · Videos {limitText(quota.videos.used, quota.videos.limit)}</span>
        )}
      </button>
      <input ref={fileInput} type="file" accept="image/*,video/*" multiple hidden onChange={(e) => { handleFiles(e.target.files); e.target.value = ''; }} />

      <form className="ob-link-row" onSubmit={handleAddLink}>
        <input className="ob-input" placeholder="Or paste a YouTube / Instagram link" value={linkUrl} onChange={(e) => setLinkUrl(e.target.value)} />
        <button type="submit" className="ob-back-btn" disabled={busy || !linkUrl.trim()}>Add</button>
      </form>

      <InlineError error={error} />

      {media.data && media.data.items.length > 0 && (
        <div className="ob-media-grid">
          {media.data.items.map((m) => (
            <div key={m.id} className="ob-media-item">
              {m.kind === 'image' ? <img src={m.url} alt={m.caption ?? ''} /> : (
                <div className="ob-media-link"><PlayCircle size={22} /> {m.kind === 'youtube' ? 'YouTube' : m.kind === 'instagram' ? 'Instagram' : 'Video'}</div>
              )}
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
