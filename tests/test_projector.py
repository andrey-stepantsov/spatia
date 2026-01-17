
import pytest
from unittest.mock import MagicMock, patch
from backend.projector import Projector

@pytest.fixture
def mock_genai_client():
    with patch('backend.projector.genai.Client') as MockClient:
        # returns an instance
        client_instance = MockClient.return_value
        # models is an attribute
        client_instance.models = MagicMock()
        yield client_instance

def test_gather_aura_no_context():
    proj = Projector()
    # Mocking environment variable if needed, but Projector defaults to check os.environ
    # We can rely on Projector logic, or patch os.environ in test if we want to ensure client creation
    
    system_instruction, context_str = proj.gather_aura(
        atom_id="test_atom", 
        content=";; Intent: Print hello", 
        portals=[], 
        neighbors=[]
    )
    
    assert "You are the Spatia Projector" in system_instruction
    assert "=== CONTEXT AURA for test_atom ===" in context_str
    assert ";; Intent: Print hello" in context_str
    assert "--- PORTALS ---" not in context_str

def test_gather_aura_with_context():
    proj = Projector()
    portals = [{'path': '/foo', 'description': 'bar'}]
    neighbors = ['neighbor_1']
    
    _, context_str = proj.gather_aura("atom_x", "intent", portals, neighbors)
    
    assert "--- PORTALS ---" in context_str
    assert "- Path: /foo (bar)" in context_str
    assert "--- THREAD NEIGHBORS ---" in context_str
    assert "- Neighbor: neighbor_1" in context_str

@patch.dict('os.environ', {'GEMINI_API_KEY': 'fake_key'})
def test_summon_success(mock_genai_client):
    proj = Projector()
    
    # Mock response
    mock_response = MagicMock()
    mock_response.text = "print('hello')"
    mock_genai_client.models.generate_content.return_value = mock_response
    
    result = proj.summon("atom1", "intent", [], [])
    
    assert result == "print('hello')"
    mock_genai_client.models.generate_content.assert_called_once()
    
    # Check arguments
    call_args = mock_genai_client.models.generate_content.call_args
    assert call_args.kwargs['model'] == 'gemini-2.5-flash' # Default

@patch.dict('os.environ', {'GEMINI_API_KEY': 'fake_key'})
def test_summon_custom_model(mock_genai_client):
    proj = Projector()
    mock_response = MagicMock()
    mock_response.text = "code"
    mock_genai_client.models.generate_content.return_value = mock_response
    
    proj.summon("atom1", "intent", [], [], model_name="gemini-3-flash")
    
    call_args = mock_genai_client.models.generate_content.call_args
    assert call_args.kwargs['model'] == 'gemini-3-flash'
