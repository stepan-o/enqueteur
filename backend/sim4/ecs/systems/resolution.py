# resolution.py (Million Dollar Version)
from ..components import (
    Perception,
    EmotionalState,
    CognitiveState,
    SocialState,
)


def resolution_system(world, dt):
    """
    Million-dollar resolution phase.
    Purpose: normalize and finalize all agent states so the next tick starts clean.
    Responsibilities:
      - clear momentary perceptions (noises/messages)
      - apply emotional decay / stabilization
      - apply cognitive drift reduction
      - prune social links
      - clean invalid focus targets
      - clamp values (safety for Godot visuals)
      - deterministic end-of-frame reset
    """

    to_remove_focus = set()

    # Pass 1: resolve all per-agent transient state
    for ent, (p, emo, cog, social) in world.query(
            Perception, EmotionalState, CognitiveState, SocialState):

        # ---------------------------------------------------------
        # 1. Clear transient perception channels
        # ---------------------------------------------------------
        p.noises.clear()
        p.messages.clear()

        # ---------------------------------------------------------
        # 2. Emotional stabilization/decay (AAA-style)
        # ---------------------------------------------------------
        emo.arousal = max(0.0, emo.arousal - 0.1 * dt)
        emo.tension = max(0.0, emo.tension - 0.05 * dt)

        # valence drifts toward neutral if unprovoked
        if abs(emo.valence) < 0.02:
            emo.valence = 0.0
        else:
            emo.valence *= (1.0 - 0.05 * dt)

        # safety clamp before sending to Godot
        emo.valence = max(-1, min(1, emo.valence))
        emo.arousal = max(0, min(1, emo.arousal))
        emo.tension = max(0, min(2, emo.tension))   # higher cap for rendering drama

        # ---------------------------------------------------------
        # 3. Cognitive dampening
        # ---------------------------------------------------------
        cog.curiosity *= (1.0 - 0.02 * dt)
        cog.confusion *= (1.0 - 0.03 * dt)

        if cog.curiosity < 0.001:
            cog.curiosity = 0.0
        if cog.confusion < 0.001:
            cog.confusion = 0.0

        # ---------------------------------------------------------
        # 4. Validate focus targets
        # ---------------------------------------------------------
        if cog.focus_entity is not None:
            if not world.entity_exists(cog.focus_entity):
                to_remove_focus.add(ent)

        # ---------------------------------------------------------
        # 5. Social state cleanup
        #    Weak ties fade. Weak ties < 0.01 disappear.
        # ---------------------------------------------------------
        dead = []
        for target, affinity in social.relationships.items():
            # fade toward zero
            new_aff = affinity * (1.0 - 0.02 * dt)
            if abs(new_aff) < 0.01:
                dead.append(target)
            else:
                social.relationships[target] = new_aff

        for target in dead:
            del social.relationships[target]

    # -------------------------------------------------------------
    # Pass 2: apply focus cleanup (can't modify mid-query)
    # -------------------------------------------------------------
    for ent in to_remove_focus:
        cog = world.get_component(ent, CognitiveState)
        if cog:
            cog.focus_entity = None
