# Geometric Lisp (Slang B) Specification

This language maps logic (Atoms) to the physical screen (tmux).

## Primitives
```lisp
;; Pin an atom to a specific location
(anchor :ID {x y})

;; Define safety and agency boundaries
(envelope :POLICY [atoms...])

;; Link to external Nix dependencies
(portal :NAME :PATH)

;; Force a visual thread between two nodes
(thread :FROM :TO)
```

## Example
```lisp
(node :NETWORK_PARSER
  (anchor :TOP_LEFT {0 0})
  (envelope :IO_RESTRICTED
    (defn parse [ptr] ...))
  (thread :NETWORK_PARSER :HW_REGS))
```
