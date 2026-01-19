import pytest
import importlib.util
import os
import sys

# Load spatia-shatter.py module dynamically since it has a dash in the name
MODULE_PATH = os.path.join(os.path.dirname(__file__), '../.spatia/bin/spatia-shatter.py')
spec = importlib.util.spec_from_file_location("spatia_shatter", MODULE_PATH)
spatia_shatter = importlib.util.module_from_spec(spec)
sys.modules["spatia_shatter"] = spatia_shatter
spec.loader.exec_module(spatia_shatter)

detect_domain = spatia_shatter.detect_domain

def test_detect_domain_culinary():
    assert detect_domain("pasta.recipe", "content") == "Culinary"
    assert detect_domain("soup.cook", "content") == "Culinary"

def test_detect_domain_legal():
    assert detect_domain("agreement.contract", "content") == "Legal"
    assert detect_domain("terms.legal", "content") == "Legal"

def test_detect_domain_software():
    assert detect_domain("script.py", "content") == "Software"
    assert detect_domain("app.js", "content") == "Software"
    assert detect_domain("comp.jsx", "content") == "Software"
    assert detect_domain("util.ts", "content") == "Software"
    assert detect_domain("view.tsx", "content") == "Software"
    assert detect_domain("main.c", "content") == "Software"
    assert detect_domain("main.cpp", "content") == "Software"
    assert detect_domain("pkg.go", "content") == "Software"
    assert detect_domain("lib.rs", "content") == "Software"
    assert detect_domain("App.java", "content") == "Software"
    assert detect_domain("Gemfile.rb", "content") == "Software"

def test_detect_domain_register():
    # Valid Register
    assert detect_domain("regs.h", "#define R 0x1000") == "Register"
    # Invalid Register (no hex)
    assert detect_domain("regs.h", "#define R 1000") == "generic"
    # Not a .h file
    assert detect_domain("regs.c", "#define R 0x1000") == "Software"

def test_detect_domain_generic():
    assert detect_domain("readme.md", "content") == "generic"
    assert detect_domain("data.txt", "content") == "generic"
    assert detect_domain("image.png", "content") == "generic"
