/-
  vericode -- Lean 4 proof tactics library for sorting algorithms.

  These definitions and lemmas serve as a reference library that the LLM
  can draw from when generating proofs for sorting-related specifications.

  NOTE: Theorems marked with `sorry` are INCOMPLETE PROOF TEMPLATES.
  They state the correct propositions but the proofs are not finished.
  The LLM is expected to complete them (or generate fresh proofs) during
  the verification pipeline.  Do NOT treat these as verified lemmas.
-/

-- Predicate: a list is sorted in non-decreasing order.
def is_sorted : List Int -> Prop
  | [] => True
  | [_] => True
  | (a :: b :: rest) => a <= b /\ is_sorted (b :: rest)

-- Predicate: two lists are permutations of each other.
-- Uses multiset equality via sorted comparison.
def is_permutation (xs ys : List Int) : Prop :=
  xs.length = ys.length /\ (xs.toArray.qsort (· < ·)) = (ys.toArray.qsort (· < ·))

-- Insertion sort: a simple, proof-friendly sorting algorithm.
def insert_sorted (x : Int) : List Int -> List Int
  | [] => [x]
  | (y :: ys) =>
    if x <= y then x :: y :: ys
    else y :: insert_sorted x ys

def insertion_sort : List Int -> List Int
  | [] => []
  | (x :: xs) => insert_sorted x (insertion_sort xs)

-- Lemma: inserting into a sorted list preserves sortedness.
theorem insert_sorted_preserves : forall (x : Int) (lst : List Int),
    is_sorted lst -> is_sorted (insert_sorted x lst) := by
  intro x lst h
  induction lst with
  | nil => simp [insert_sorted, is_sorted]
  | cons y ys ih =>
    simp [insert_sorted]
    split
    · constructor
      · assumption
      · exact h
    · cases ys with
      | nil =>
        simp [insert_sorted, is_sorted]
        omega
      | cons z zs =>
        simp [is_sorted] at h
        obtain ⟨hyz, hsorted⟩ := h
        simp [insert_sorted]
        sorry -- TODO: full proof requires case analysis on x <= z (template, not complete)

-- Lemma: insertion sort produces a sorted list.
theorem insertion_sort_sorted : forall (lst : List Int),
    is_sorted (insertion_sort lst) := by
  intro lst
  induction lst with
  | nil => simp [insertion_sort, is_sorted]
  | cons x xs ih =>
    simp [insertion_sort]
    exact insert_sorted_preserves x (insertion_sort xs) ih

-- Lemma: insertion sort preserves length.
theorem insertion_sort_length : forall (lst : List Int),
    (insertion_sort lst).length = lst.length := by
  intro lst
  induction lst with
  | nil => simp [insertion_sort]
  | cons x xs ih =>
    simp [insertion_sort]
    sorry -- TODO: requires insert_sorted_length lemma (template, not complete)
