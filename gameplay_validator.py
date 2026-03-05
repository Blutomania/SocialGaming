"""
Choose Your Mystery - Gameplay Validator
=========================================

Validates that a generated mystery creates fair, solvable, strategic gameplay.

Validation checks:
  1. Solvability      — enough critical clues, all suspects have motives,
                        red herring ratio balanced, solution references real clue IDs,
                        exactly one culprit character
  2. Red herring fairness — every red herring has what_disproves_it populated
  3. Setting coherence — evidence categories valid for the world's tech level
  4. Interrogation coverage — critical testimonials have trigger conditions,
                              each suspect's knowledge_that_helps_solve is populated
  5. Info sharing (75/25) — enough total clues for meaningful withholding decisions
  6. Difficulty scoring — calibrated from suspect count, red herrings, evidence clarity

The 75/25 Sharing Rule
-----------------------
Each round, players must share 75% of what they've discovered, keeping 25% private.
For this to create meaningful decisions:
  - Total clues (physical + testimonial) should be >= 8
  - At least one critical clue should require active investigation to obtain
    (analysis_required=True, or a testimonial with a non-trivial trigger_condition)

Usage
-----
    from gameplay_validator import MysteryGameplayValidator
    v = MysteryGameplayValidator("./mystery_database/scenarios/the_locked_room_mystery.json")
    print(v.generate_full_report(num_players=4))

Or run directly:
    python gameplay_validator.py
"""

import json
from typing import Dict, List


VALID_CATEGORIES = {
    'pre_industrial': {'physical', 'chemical', 'documentary', 'testimonial', 'environmental'},
    'industrial':     {'physical', 'chemical', 'documentary', 'testimonial', 'environmental'},
    'contemporary':   {'physical', 'chemical', 'documentary', 'testimonial', 'environmental', 'digital'},
    'advanced':       {'physical', 'biological', 'chemical', 'documentary', 'testimonial', 'environmental', 'digital'},
    'sci_fi':         {'physical', 'biological', 'chemical', 'documentary', 'testimonial', 'environmental', 'digital'},
}


class MysteryGameplayValidator:

    def __init__(self, scenario_path: str):
        with open(scenario_path, 'r') as f:
            self.mystery = json.load(f)

    # -------------------------------------------------------------------------

    def validate_solvability(self) -> Dict:
        issues = []
        warnings = []

        physical_clues = self.mystery.get('physical_clues', [])
        testimonials = self.mystery.get('testimonial_revelations', [])
        characters = self.mystery.get('characters', [])
        solution_steps = self.mystery.get('solution_steps', [])
        culprit_name = self.mystery.get('culprit_name', '')

        # Rule 1: At least 2 critical physical clues
        critical_physical = [c for c in physical_clues if c.get('relevance') == 'critical']
        if len(critical_physical) < 2:
            issues.append(f"Only {len(critical_physical)} critical physical clue(s). Need at least 2.")

        # Rule 2: At least 1 critical testimonial
        critical_testimonial = [t for t in testimonials if t.get('relevance') == 'critical']
        if len(critical_testimonial) < 1:
            warnings.append("No critical testimonial revelations. Interrogation may feel unrewarding.")

        # Rule 3: All suspects have motives
        suspects = [c for c in characters if c.get('role') == 'suspect']
        missing_motive = [c['name'] for c in suspects if not c.get('motive')]
        if missing_motive:
            issues.append(f"Suspects without motives: {missing_motive}")

        # Rule 4: Red herring ratio 20-50% of total clues
        all_clues = physical_clues + testimonials
        total = len(all_clues)
        red_herrings = [c for c in all_clues if c.get('relevance') == 'red_herring']
        rh_ratio = len(red_herrings) / total if total > 0 else 0
        if rh_ratio > 0.5:
            warnings.append(f"{int(rh_ratio * 100)}% red herrings — may frustrate players.")
        elif rh_ratio < 0.2 and total > 0:
            warnings.append(f"Only {int(rh_ratio * 100)}% red herrings — mystery may be too easy.")

        # Rule 5: Culprit exists and matches exactly one character with is_culprit=True
        culprit_flagged = [c for c in characters if c.get('is_culprit')]
        if len(culprit_flagged) == 0:
            issues.append("No character has is_culprit=True.")
        elif len(culprit_flagged) > 1:
            issues.append(f"Multiple characters have is_culprit=True: {[c['name'] for c in culprit_flagged]}")
        elif culprit_flagged[0]['name'] != culprit_name:
            issues.append(
                f"culprit_name '{culprit_name}' does not match the character "
                f"with is_culprit=True ('{culprit_flagged[0]['name']}')."
            )

        # Rule 6: Solution steps reference real clue IDs
        all_clue_ids = {c.get('id') for c in physical_clues} | {t.get('id') for t in testimonials}
        for step in solution_steps:
            bad_refs = [cid for cid in step.get('clue_ids', []) if cid not in all_clue_ids]
            if bad_refs:
                issues.append(f"Solution step {step.get('step_number')} references unknown IDs: {bad_refs}")

        if not solution_steps:
            warnings.append("No solution_steps defined. Validator cannot score partial solutions.")

        return {
            'solvable': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'critical_physical_count': len(critical_physical),
            'critical_testimonial_count': len(critical_testimonial),
            'red_herring_count': len(red_herrings),
            'red_herring_ratio': rh_ratio,
            'suspect_count': len(suspects),
            'total_clues': total
        }

    def validate_red_herring_fairness(self) -> Dict:
        """Every red herring must have what_disproves_it populated."""
        issues = []
        warnings = []

        physical_clues = self.mystery.get('physical_clues', [])
        testimonials = self.mystery.get('testimonial_revelations', [])
        all_clue_ids = {c.get('id') for c in physical_clues} | {t.get('id') for t in testimonials}

        unfair = []
        for clue in physical_clues + testimonials:
            if clue.get('relevance') == 'red_herring':
                disproves = clue.get('what_disproves_it')
                if not disproves:
                    unfair.append(clue.get('id', '?'))
                elif disproves not in all_clue_ids:
                    warnings.append(
                        f"Red herring '{clue.get('id')}' references unknown disproof: '{disproves}'"
                    )

        if unfair:
            issues.append(
                f"Red herrings without what_disproves_it (unfair): {unfair}"
            )

        return {
            'fair': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'unfair_red_herrings': unfair
        }

    def validate_setting_coherence(self) -> Dict:
        """Evidence categories must be valid for the world's tech_level."""
        issues = []
        warnings = []

        tech_level = self.mystery.get('world_tech_level', 'contemporary')
        physical_clues = self.mystery.get('physical_clues', [])
        valid = VALID_CATEGORIES.get(tech_level, set())

        incoherent = []
        for clue in physical_clues:
            cat = clue.get('category', 'physical')
            if valid and cat not in valid:
                incoherent.append(f"'{clue.get('name', clue.get('id'))}' ({cat})")

        if incoherent:
            issues.append(
                f"Evidence categories invalid for tech_level='{tech_level}': {incoherent}"
            )

        if not self.mystery.get('world_physics_constraints'):
            era = self.mystery.get('world_era', '')
            if era not in ('modern', 'near_future', 'far_future'):
                warnings.append(
                    f"No world_physics_constraints defined for era='{era}'. "
                    "Historical settings should document investigation limits."
                )

        return {
            'coherent': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'tech_level': tech_level,
            'incoherent_evidence': incoherent
        }

    def validate_interrogation_coverage(self) -> Dict:
        """
        Check that interrogation mechanics are properly set up:
        - Critical testimonials have trigger conditions
        - Each suspect has knowledge_that_helps_solve populated
        - Characters have interrogation_behavior populated
        """
        issues = []
        warnings = []

        testimonials = self.mystery.get('testimonial_revelations', [])
        characters = self.mystery.get('characters', [])
        suspects = [c for c in characters if c.get('role') == 'suspect']

        # Critical testimonials must have trigger conditions
        for t in testimonials:
            if t.get('relevance') == 'critical' and not t.get('trigger_condition'):
                issues.append(
                    f"Critical testimonial '{t.get('id')}' has no trigger_condition. "
                    "Players need to know how to unlock it."
                )

        # Suspects should have knowledge_that_helps_solve
        suspects_without_knowledge = [
            c['name'] for c in suspects
            if not c.get('knowledge_that_helps_solve')
        ]
        if suspects_without_knowledge:
            warnings.append(
                f"Suspects without knowledge_that_helps_solve: {suspects_without_knowledge}. "
                "Interrogating these characters will feel unrewarding."
            )

        # Characters should have interrogation_behavior
        missing_behavior = [
            c['name'] for c in characters
            if not c.get('interrogation_behavior') and c.get('role') != 'victim'
        ]
        if missing_behavior:
            warnings.append(
                f"Characters without interrogation_behavior: {missing_behavior}"
            )

        return {
            'adequate': len(issues) == 0,
            'issues': issues,
            'warnings': warnings
        }

    def validate_information_sharing(self, num_players: int = 4) -> Dict:
        """Check that the 75/25 sharing mechanic creates meaningful decisions."""
        physical_clues = self.mystery.get('physical_clues', [])
        testimonials = self.mystery.get('testimonial_revelations', [])
        total = len(physical_clues) + len(testimonials)

        avg_per_turn = 2
        items_after_3_turns = avg_per_turn * 3
        must_share = int(items_after_3_turns * 0.75)
        can_hide = items_after_3_turns - must_share

        if total < 6:
            depth = "LOW"
            note = f"Only {total} total clues — not enough for meaningful withholding."
        elif total < 10:
            depth = "MEDIUM"
            note = "Adequate clues for strategic decisions."
        else:
            depth = "HIGH"
            note = "Rich evidence landscape creates complex strategic choices."

        # Any clue that requires active effort to obtain is worth withholding
        active_clues = [c for c in physical_clues if c.get('analysis_required')]
        gated_testimonials = [
            t for t in testimonials
            if t.get('trigger_condition') and
               t.get('relevance') in ('critical', 'supporting') and
               'second' in t.get('trigger_condition', '').lower()
        ]

        return {
            'strategic_depth': depth,
            'total_clues': total,
            'physical_clues': len(physical_clues),
            'testimonials': len(testimonials),
            'items_per_player_estimate': items_after_3_turns,
            'must_share_count': must_share,
            'can_hide_count': can_hide,
            'active_investigation_clues': len(active_clues) + len(gated_testimonials),
            'note': note
        }

    def estimate_difficulty(self) -> Dict:
        """
        Three-factor difficulty score (3-9 → EASY/MEDIUM/HARD):
          1. Suspect count
          2. Red herring ratio
          3. Critical clue clarity
        """
        characters = self.mystery.get('characters', [])
        physical_clues = self.mystery.get('physical_clues', [])
        testimonials = self.mystery.get('testimonial_revelations', [])
        all_clues = physical_clues + testimonials

        suspects = [c for c in characters if c.get('role') == 'suspect']
        critical = [c for c in all_clues if c.get('relevance') == 'critical']
        red_herrings = [c for c in all_clues if c.get('relevance') == 'red_herring']
        total = len(all_clues)

        score = 0
        factors = []

        if len(suspects) <= 3:
            score += 1
            factors.append("Few suspects (easy)")
        elif len(suspects) <= 5:
            score += 2
            factors.append("Moderate suspect pool (medium)")
        else:
            score += 3
            factors.append("Large suspect pool (hard)")

        rh_ratio = len(red_herrings) / total if total > 0 else 0
        if rh_ratio < 0.25:
            score += 1
            factors.append("Few red herrings (easy)")
        elif rh_ratio < 0.40:
            score += 2
            factors.append("Balanced misdirection (medium)")
        else:
            score += 3
            factors.append("Heavy misdirection (hard)")

        if len(critical) >= 4:
            score += 1
            factors.append("Clear evidence trail (easy)")
        elif len(critical) >= 2:
            score += 2
            factors.append("Moderate evidence trail (medium)")
        else:
            score += 3
            factors.append("Scarce critical clues (hard)")

        difficulty = "EASY" if score <= 4 else "MEDIUM" if score <= 6 else "HARD"

        return {
            'difficulty': difficulty,
            'score': score,
            'max_score': 9,
            'factors': factors,
            'estimated_playtime': self._estimate_playtime(difficulty, len(suspects))
        }

    def _estimate_playtime(self, difficulty: str, suspect_count: int) -> str:
        base = 20 + (suspect_count * 5)
        return {
            "EASY":   f"{base}-{base + 15} minutes",
            "MEDIUM": f"{base + 10}-{base + 30} minutes",
            "HARD":   f"{base + 20}-{base + 45} minutes"
        }[difficulty]

    def generate_full_report(self, num_players: int = 4) -> str:
        solvability = self.validate_solvability()
        fairness = self.validate_red_herring_fairness()
        coherence = self.validate_setting_coherence()
        interrogation = self.validate_interrogation_coverage()
        sharing = self.validate_information_sharing(num_players)
        difficulty = self.estimate_difficulty()

        sep = "=" * 70
        lines = [
            sep,
            "MYSTERY GAMEPLAY VALIDATION REPORT",
            sep,
            "",
            f"Mystery:     {self.mystery.get('title', 'Unknown')}",
            f"Period:      {self.mystery.get('world_specific_period', '?')}",
            f"Tech Level:  {self.mystery.get('world_tech_level', '?')}",
            f"Crime:       {self.mystery.get('crime_type', '?')} / {self.mystery.get('mystery_type', '?')}",
            f"Stakes:      {self.mystery.get('stakes', '?')}",
            f"Players:     {num_players}",
            "",
        ]

        def section(title, result, pass_key=None):
            lines.append(title)
            lines.append("-" * 70)
            if pass_key is not None:
                lines.append("PASS" if result.get(pass_key) else "FAIL")
            if result.get('issues'):
                lines.append("\nCritical Issues:")
                lines.extend(f"  [!] {i}" for i in result['issues'])
            if result.get('warnings'):
                lines.append("\nWarnings:")
                lines.extend(f"  [~] {w}" for w in result['warnings'])
            lines.append("")

        section("SOLVABILITY", solvability, 'solvable')
        lines[-1:] = [
            f"Critical physical clues:  {solvability['critical_physical_count']}",
            f"Critical testimonials:    {solvability['critical_testimonial_count']}",
            f"Red herring ratio:        {int(solvability['red_herring_ratio'] * 100)}%",
            f"Suspects:                 {solvability['suspect_count']}",
            ""
        ]

        section("RED HERRING FAIRNESS", fairness, 'fair')
        section("SETTING COHERENCE", coherence, 'coherent')
        section("INTERROGATION COVERAGE", interrogation, 'adequate')

        lines += [
            "INFORMATION SHARING (75/25 Rule)",
            "-" * 70,
            f"Strategic Depth:          {sharing['strategic_depth']}",
            f"Total Clues:              {sharing['total_clues']} ({sharing['physical_clues']} physical + {sharing['testimonials']} testimonial)",
            f"Active investigation:     {sharing['active_investigation_clues']} clues require effort to obtain",
            f"Per player after 3 turns: ~{sharing['items_per_player_estimate']} items",
            f"  Must share (75%):       ~{sharing['must_share_count']}",
            f"  Can withhold:           ~{sharing['can_hide_count']}",
            f"  {sharing['note']}",
            ""
        ]

        lines += [
            "DIFFICULTY ASSESSMENT",
            "-" * 70,
            f"Difficulty:        {difficulty['difficulty']}",
            f"Score:             {difficulty['score']}/{difficulty['max_score']}",
            f"Estimated Playtime: {difficulty['estimated_playtime']}",
            "\nFactors:",
        ]
        lines.extend(f"  - {f}" for f in difficulty['factors'])
        lines.append("")

        all_issues = (
            solvability['issues'] + fairness['issues'] +
            coherence['issues'] + interrogation['issues']
        )
        all_warnings = (
            solvability['warnings'] + fairness['warnings'] +
            coherence['warnings'] + interrogation['warnings']
        )

        lines += ["RECOMMENDATION", "-" * 70]
        if all_issues:
            lines.append("FAIL — Fix critical issues before use:")
            lines.extend(f"  [!] {i}" for i in all_issues)
        elif all_warnings:
            lines.append("PASS with warnings — Playable but could be improved.")
        else:
            lines.append("PASS — Mystery is ready for gameplay.")

        lines += ["", sep]
        return "\n".join(lines)


if __name__ == "__main__":
    import os
    path = "./mystery_database/scenarios/the_locked_room_mystery.json"
    if not os.path.exists(path):
        print(f"Demo scenario not found: {path}")
        print("Run demo_acquisition.py first.")
        exit(1)
    validator = MysteryGameplayValidator(path)
    print(validator.generate_full_report(num_players=4))
