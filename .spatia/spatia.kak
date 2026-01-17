# Spatia Editor Integration

# Epistemic Glow Faces
set-face global SpatiaShadow  blue,default+b
set-face global SpatiaClaim   yellow,default+i
set-face global SpatiaEndorsed green,default+b

# Endorsement Command
define-command endorse -docstring "Endorse the selected Atom (Level 3)" %{
    exec -save-regs 'a' ' %{ "ay }
    # Call sentinel update via shell
    nop %sh{
        # logic to update DB status to 3
    }
    echo "Atom Endorsed."
}
