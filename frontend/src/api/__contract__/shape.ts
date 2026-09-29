// Type-level structural check for JSON examples. JSON imports widen string
// literals, so `satisfies ArtistCard` would fail on enums; instead we compare
// key sets recursively: a missing, extra or misspelled key is a compile error.

type Primitive = string | number | boolean | null | undefined;

/** Contract type with every leaf widened to `unknown`, keys preserved. */
export type Shape<T> = T extends Primitive
  ? unknown
  : T extends readonly (infer E)[]
    ? Shape<E>[]
    : { [K in keyof T]-?: Shape<T[K]> };

/** Maps any key of U that S does not declare to `never`, recursively. */
export type NoExtraKeys<S, U> = U extends readonly (infer UE)[]
  ? S extends readonly (infer SE)[]
    ? NoExtraKeys<SE, UE>[]
    : U
  : U extends object
    ? S extends object
      ? { [K in keyof U]: K extends keyof S ? NoExtraKeys<S[K], U[K]> : never }
      : U
    : U;

/** `check<ArtistCard>()(json)` compiles only if json has exactly ArtistCard's keys. */
export function check<T>() {
  return <U extends Shape<T>>(value: U & NoExtraKeys<Shape<T>, U>): U => value;
}
