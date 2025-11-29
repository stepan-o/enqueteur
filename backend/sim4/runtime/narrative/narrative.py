import openai
import os
from typing import Dict, Any

# Ensure the OpenAI API key is set in the environment
openai.api_key = os.getenv("OPENAI_API_KEY")

# Sample Agent class to illustrate the required data structure for agents
class Agent:
    def __init__(self, agent_id: int, beliefs: Dict[str, Any], emotions: Dict[str, Any]):
        self.agent_id = agent_id
        self.beliefs = beliefs
        self.emotions = emotions

    def get_agent_state(self) -> str:
        """
        Returns a textual summary of the agent's current beliefs and emotional state.
        This will be used as a prompt for the LLM to generate dialogue or reflections.
        """
        belief_state = "\n".join([f"{key}: {value}" for key, value in self.beliefs.items()])
        emotion_state = "\n".join([f"{key}: {value}" for key, value in self.emotions.items()])
        return f"Agent {self.agent_id} Beliefs:\n{belief_state}\n\nEmotions:\n{emotion_state}"


class NarrativeEngine:
    def __init__(self, agent: Agent):
        self.agent = agent

    def generate_dialogue(self, prompt: str) -> str:
        """
        Generate dialogue based on the current agent state (beliefs, emotions).
        This will be sent to OpenAI's GPT for generation.
        """
        try:
            response = openai.Completion.create(
                model="text-davinci-003",  # Using GPT-3 here, adjust model if necessary
                prompt=prompt,
                max_tokens=150,
                temperature=0.7,  # Adjust creativity level
                n=1,
                stop=None,
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0
            )

            # Extract the response text
            dialogue = response.choices[0].text.strip()
            return dialogue

        except Exception as e:
            print(f"Error generating dialogue: {e}")
            return "I have nothing to say right now."


def generate_narrative_for_agent(agent: Agent) -> str:
    """
    Generate the narrative (e.g., dialogue, reflection) based on agent's beliefs and emotions.
    This will use the NarrativeEngine to create human-like interaction or reflection text.
    """
    # Get agent state (beliefs + emotions) to build the prompt
    agent_state = agent.get_agent_state()

    # Build the prompt to send to OpenAI GPT
    prompt = f"Based on the following beliefs and emotions of the agent, generate a dialogue or reflection:\n\n{agent_state}\n\nDialogue or reflection:"

    # Generate dialogue using OpenAI API
    narrative_engine = NarrativeEngine(agent)
    dialogue = narrative_engine.generate_dialogue(prompt)

    return dialogue


# Example usage
if __name__ == "__main__":
    # Example agent with beliefs and emotions
    beliefs = {
        "trust": "high",
        "goal": "help others",
        "self-image": "protector"
    }
    emotions = {
        "fear": "low",
        "anger": "medium",
        "happiness": "high"
    }

    agent = Agent(agent_id=1, beliefs=beliefs, emotions=emotions)

    # Generate narrative for this agent
    narrative = generate_narrative_for_agent(agent)

    print(f"Generated Narrative for Agent {agent.agent_id}: {narrative}")
