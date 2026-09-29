// Standard loading / error / empty rendering for a TanStack query result.
import type { ReactNode } from 'react';
import type { UseQueryResult } from '@tanstack/react-query';
import { errorMessage } from '../api/errors';
import './QueryState.css';

export function InlineError({ error }: { error: unknown }) {
  if (!error) return null;
  return <div className="qs-inline-error" role="alert">{errorMessage(error)}</div>;
}

interface Props<T> {
  query: UseQueryResult<T>;
  children: (data: T) => ReactNode;
  loading?: ReactNode;
  isEmpty?: (data: T) => boolean;
  empty?: ReactNode;
}

export default function QueryState<T>({ query, children, loading, isEmpty, empty }: Props<T>) {
  if (query.isPending) {
    return <>{loading ?? <div className="qs-block" role="status"><span className="qs-spinner" aria-hidden="true" /></div>}</>;
  }
  if (query.isError) {
    return (
      <div className="qs-block" role="alert">
        <span className="qs-error-title">Couldn't load this</span>
        <span className="qs-label">{errorMessage(query.error)}</span>
        <button type="button" className="qs-retry" onClick={() => query.refetch()}>Try again</button>
      </div>
    );
  }
  if (isEmpty?.(query.data) && empty) return <>{empty}</>;
  return <>{children(query.data)}</>;
}
