# The Geometric Lisp Semantic Engine

## Spatial Rules
- **Anchors are Absolute:** If an Anchor is set to `{10, 20}`, that Atom starts on line 10, col 20 of the tmux pane.
- **Collisions:** If two Atoms overlap, the UI renders a **"Conflict Fold"**. The Human must resolve this by moving an Anchor.
- **Visual Threads:** Threads are not just decorations. They are **Dependency Constraints**. If you delete a Thread in Slang B, the system must warn you that the C++ logic in Slang A might now be unreachable.

## Transformation Logic
When the Human moves a tmux pane, the **Projector Agent** updates the `geometry.sp` file in real-time. The Geometry is the *Source*, the View is the *Projection*.
