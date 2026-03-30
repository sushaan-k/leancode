/-
  vericode -- Lean 4 proof tactics library for searching algorithms.

  Reference definitions and lemmas for binary search and related
  algorithms.  The LLM uses these as context when generating proofs.

  NOTE: Theorems marked with `sorry` are INCOMPLETE PROOF TEMPLATES.
  They state the correct propositions but the proofs are not finished.
  The LLM is expected to complete them (or generate fresh proofs) during
  the verification pipeline.  Do NOT treat these as verified lemmas.
-/

-- Predicate: a list is sorted (reused from sorting.lean in practice,
-- duplicated here for standalone use).
def is_sorted_list : List Int -> Prop
  | [] => True
  | [_] => True
  | (a :: b :: rest) => a <= b /\ is_sorted_list (b :: rest)

-- Binary search on an array (modelled as a function from Nat to Int).
-- Returns the index of `target` or -1 if not found.
def binary_search_aux (arr : Array Int) (target : Int) (lo hi : Nat) : Int :=
  if lo > hi then -1
  else
    let mid := (lo + hi) / 2
    if h : mid < arr.size then
      let v := arr[mid]
      if v == target then mid
      else if v < target then binary_search_aux arr target (mid + 1) hi
      else
        if mid == 0 then -1
        else binary_search_aux arr target lo (mid - 1)
    else -1

def binary_search (arr : Array Int) (target : Int) : Int :=
  if arr.size == 0 then -1
  else binary_search_aux arr target 0 (arr.size - 1)

-- Specification: if binary_search returns a non-negative index, the
-- element at that index equals the target.
theorem binary_search_found_correct :
    forall (arr : Array Int) (target : Int),
    let idx := binary_search arr target
    idx >= 0 -> (h : idx.toNat < arr.size) -> arr[idx.toNat] = target := by
  sorry -- TODO: proof requires induction on the recursive structure (template, not complete)

-- Specification: if binary_search returns -1 and the array is sorted,
-- the target is not in the array.
theorem binary_search_not_found_correct :
    forall (arr : Array Int) (target : Int),
    is_sorted_list arr.toList ->
    binary_search arr target = -1 ->
    target ∉ arr.toList := by
  sorry -- TODO: requires auxiliary lemmas about sorted subarrays (template, not complete)

-- Linear search correctness (simpler, useful as a warm-up proof).
def linear_search (lst : List Int) (target : Int) : Int :=
  match lst with
  | [] => -1
  | (x :: xs) =>
    if x == target then 0
    else
      let r := linear_search xs target
      if r == -1 then -1 else r + 1

theorem linear_search_found :
    forall (lst : List Int) (target : Int),
    let idx := linear_search lst target
    idx >= 0 -> lst.get? idx.toNat = some target := by
  sorry -- TODO: template, not complete
