/-
  vericode -- Lean 4 proof tactics library for data structures.

  Reference definitions and lemmas for binary search trees, linked
  lists, and other fundamental data structures.

  NOTE: Theorems marked with `sorry` are INCOMPLETE PROOF TEMPLATES.
  They state the correct propositions but the proofs are not finished.
  The LLM is expected to complete them (or generate fresh proofs) during
  the verification pipeline.  Do NOT treat these as verified lemmas.
-/

-- Binary search tree
inductive BST where
  | leaf : BST
  | node : Int -> BST -> BST -> BST

-- BST invariant: all left children < root, all right children >= root.
def bst_valid : BST -> Prop
  | BST.leaf => True
  | BST.node v left right =>
    bst_valid left /\
    bst_valid right /\
    (forall x, bst_member x left -> x < v) /\
    (forall x, bst_member x right -> x >= v)
where
  bst_member : Int -> BST -> Prop
    | _, BST.leaf => False
    | x, BST.node v left right =>
      x = v \/ bst_member x left \/ bst_member x right

-- BST membership
def bst_member : Int -> BST -> Prop
  | _, BST.leaf => False
  | x, BST.node v left right =>
    x = v \/ bst_member x left \/ bst_member x right

-- BST insertion
def bst_insert (x : Int) : BST -> BST
  | BST.leaf => BST.node x BST.leaf BST.leaf
  | BST.node v left right =>
    if x < v then BST.node v (bst_insert x left) right
    else BST.node v left (bst_insert x right)

-- Theorem: insertion preserves the BST invariant.
theorem bst_insert_valid :
    forall (x : Int) (t : BST),
    bst_valid t -> bst_valid (bst_insert x t) := by
  sorry -- TODO: requires structural induction + case analysis (template, not complete)

-- Theorem: the inserted element is a member after insertion.
theorem bst_insert_member :
    forall (x : Int) (t : BST),
    bst_member x (bst_insert x t) := by
  intro x t
  induction t with
  | leaf => simp [bst_insert, bst_member]
  | node v left right ih_l ih_r =>
    simp [bst_insert]
    split
    · left; right; left; exact ih_l
    · left; right; right; exact ih_r

-- BST size
def bst_size : BST -> Nat
  | BST.leaf => 0
  | BST.node _ left right => 1 + bst_size left + bst_size right

-- Theorem: insertion increases size by exactly 1 (if element is new).
theorem bst_insert_size :
    forall (x : Int) (t : BST),
    ¬ bst_member x t ->
    bst_size (bst_insert x t) = bst_size t + 1 := by
  sorry -- TODO: template, not complete

-- In-order traversal yields a sorted list for a valid BST.
def bst_inorder : BST -> List Int
  | BST.leaf => []
  | BST.node v left right =>
    bst_inorder left ++ [v] ++ bst_inorder right
