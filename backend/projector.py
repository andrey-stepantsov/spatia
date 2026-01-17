
import os
from google import genai
from google.genai import types

class Projector:
    def __init__(self):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            print("WARNING: GEMINI_API_KEY not set. Summons will fail.")
            self.client = None
        else:
            self.client = genai.Client(api_key=api_key)

    def gather_aura(self, atom_id: str, content: str, portals: list, neighbors: list) -> str:
        """
        Constructs the system prompt and context for the AI.
        """
        system_instruction = (
            "You are the Spatia Projector. Translate the provided Slang B (Lisp Intent) into a Slang A (Python/YAML/C++) implementation. "
            "Adhere strictly to constraints in the provided Portals. Output raw code/data only—no markdown, no chat."
        )

        context_str = f"=== CONTEXT AURA for {atom_id} ===\n"
        
        if portals:
            context_str += "\n--- PORTALS ---\n"
            for p in portals:
                 # In a real implementation we might fetch content, here we just list paths/desc
                 context_str += f"- Path: {p.get('path')} ({p.get('description') or 'No Desc'})\n"
        
        if neighbors:
            context_str += "\n--- THREAD NEIGHBORS ---\n"
            for n in neighbors:
                context_str += f"- Neighbor: {n}\n"

        context_str += f"\n--- INTENT (SLANG B) ---\n{content}\n"
        
        return system_instruction, context_str

    def summon(self, atom_id: str, content: str, portals: list, neighbors: list, model_name: str = "gemini-2.5-flash") -> str:
        if not self.client:
             return ";; Error: GEMINI_API_KEY not set."
             
        system_instruction, user_content = self.gather_aura(atom_id, content, portals, neighbors)
        
        try:
            # google-genai SDK usage
            # Mapping model names if necessary, but we expect standard names to work.
            
            response = self.client.models.generate_content(
                model=model_name,
                contents=[user_content],
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.2 # Low temp for code generation
                )
            )
            
            if response.text:
                return response.text
            else:
                return ";; Error: No content generated."
                
        except Exception as e:
            return f";; Error during summoning: {str(e)}"
