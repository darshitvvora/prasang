import './QueryState.css';

export default function FullPageSpinner({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="qs-fullpage" role="status" aria-live="polite">
      <span className="qs-spinner" aria-hidden="true" />
      <span className="qs-label">{label}</span>
    </div>
  );
}
