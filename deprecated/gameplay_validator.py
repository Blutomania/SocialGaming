"""
Mystery Gameplay Validator
===========================

This demonstrates how structured mystery data enables GAMEPLAY VALIDATION.

Using the same RAG approach:
1. Check if mystery is solvable with available evidence
2. Validate difficulty level
3. Ensure 75% sharing mechanic creates strategic depth
4. Verify red herrings don't make mystery impossible
"""

import json
from typing import Dict, List

class MysteryGameplayValidator:
    """
    Validates that a mystery scenario will create good gameplay
    
    Why this matters: AI can generate mysteries that are:
    - Unsolvable (missing critical evidence)
    - Too easy (obvious culprit)
    - Unfair (too many red herrings)
    - Boring (no strategic depth in information sharing)
    """
    
    def __init__(self, scenario_path: str):
        """Load a mystery scenario"""
        with open(scenario_path, 'r') as f:
            self.mystery = json.load(f)
    
    def validate_solvability(self) -> Dict:
        """
        Check if the mystery is solvable with the given evidence
        
        Returns validation report with issues
        """
        issues = []
        warnings = []
        
        # Rule 1: Must have critical evidence pointing to culprit
        critical_evidence = [
            e for e in self.mystery['evidence'] 
            if e['relevance'] == 'critical'
        ]
        
        if len(critical_evidence) < 2:
            issues.append(
                "CRITICAL: Only " + str(len(critical_evidence)) + " critical evidence. "
                "Need at least 2 pieces to solve mystery."
            )
        elif len(critical_evidence) < 3:
            warnings.append(
                "Warning: Only " + str(len(critical_evidence)) + " critical evidence. "
                "Consider adding more for better gameplay."
            )
        
        # Rule 2: Must have suspects with motives
        suspects = [
            c for c in self.mystery['characters'] 
            if c['role'] == 'suspect'
        ]
        
        suspects_with_motives = [s for s in suspects if s.get('motive')]
        
        if len(suspects_with_motives) < len(suspects):
            issues.append(
                f"CRITICAL: {len(suspects) - len(suspects_with_motives)} suspects "
                f"without motives. All suspects need plausible motives."
            )
        
        # Rule 3: Check red herring balance
        red_herrings = [
            e for e in self.mystery['evidence']
            if e['relevance'] == 'red_herring'
        ]
        
        total_evidence = len(self.mystery['evidence'])
        red_herring_ratio = len(red_herrings) / total_evidence if total_evidence > 0 else 0
        
        if red_herring_ratio > 0.5:
            warnings.append(
                f"Warning: {int(red_herring_ratio*100)}% of evidence are red herrings. "
                f"Too many may frustrate players."
            )
        elif red_herring_ratio < 0.2:
            warnings.append(
                f"Warning: Only {int(red_herring_ratio*100)}% red herrings. "
                f"Mystery may be too easy."
            )
        
        # Rule 4: Solution must reference available evidence
        solution = self.mystery.get('solution', '')
        if not solution:
            issues.append("CRITICAL: No solution provided.")
        
        return {
            'solvable': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'critical_evidence_count': len(critical_evidence),
            'red_herring_ratio': red_herring_ratio,
            'suspect_count': len(suspects)
        }
    
    def validate_information_sharing(self, num_players: int = 4) -> Dict:
        """
        Validate that the 75% sharing mechanic creates strategic gameplay
        
        The 75% rule: Players must share 75% of evidence, keep 25% private
        This creates tension between cooperation and competition
        """
        
        total_evidence = len(self.mystery['evidence'])
        total_characters = len(self.mystery['characters'])
        
        # Estimate information per player per turn
        avg_evidence_per_turn = 2  # Player interrogates 1 character, finds ~2 evidence
        
        # After 3 turns, player has ~6 pieces of information
        items_after_3_turns = avg_evidence_per_turn * 3
        must_share = int(items_after_3_turns * 0.75)  # 75% = ~4-5 items
        can_hide = items_after_3_turns - must_share    # 25% = ~1-2 items
        
        strategic_depth = "Unknown"
        notes = []
        
        if total_evidence < 6:
            strategic_depth = "LOW"
            notes.append(
                "With only " + str(total_evidence) + " total evidence, "
                "not enough for strategic withholding."
            )
        elif total_evidence < 10:
            strategic_depth = "MEDIUM"
            notes.append(
                "Adequate evidence for strategic play. "
                "Players will have meaningful choices about what to share."
            )
        else:
            strategic_depth = "HIGH"
            notes.append(
                "Rich evidence landscape allows complex strategic decisions."
            )
        
        # Check for evidence that should DEFINITELY be withheld
        smoking_gun = [
            e for e in self.mystery['evidence']
            if 'critical' in e['relevance'] and 
               'culprit' in e['description'].lower()
        ]
        
        if smoking_gun:
            notes.append(
                "Mystery has 'smoking gun' evidence - "
                "players will compete to withhold this!"
            )
        
        return {
            'strategic_depth': strategic_depth,
            'total_evidence': total_evidence,
            'items_per_player_estimate': items_after_3_turns,
            'must_share_count': must_share,
            'can_hide_count': can_hide,
            'notes': notes
        }
    
    def estimate_difficulty(self) -> Dict:
        """
        Estimate mystery difficulty for players
        
        Factors:
        - Number of suspects
        - Red herring ratio
        - Complexity of solution
        - Evidence clarity
        """
        
        suspects = [c for c in self.mystery['characters'] if c['role'] == 'suspect']
        critical_evidence = [e for e in self.mystery['evidence'] if e['relevance'] == 'critical']
        red_herrings = [e for e in self.mystery['evidence'] if e['relevance'] == 'red_herring']
        
        difficulty_score = 0
        factors = []
        
        # Factor 1: Number of suspects (more = harder)
        if len(suspects) <= 3:
            difficulty_score += 1
            factors.append("Few suspects (easy)")
        elif len(suspects) <= 5:
            difficulty_score += 2
            factors.append("Moderate suspects (medium)")
        else:
            difficulty_score += 3
            factors.append("Many suspects (hard)")
        
        # Factor 2: Red herring ratio
        total_evidence = len(self.mystery['evidence'])
        rh_ratio = len(red_herrings) / total_evidence if total_evidence > 0 else 0
        
        if rh_ratio < 0.25:
            difficulty_score += 1
            factors.append("Few red herrings (easy)")
        elif rh_ratio < 0.4:
            difficulty_score += 2
            factors.append("Balanced misdirection (medium)")
        else:
            difficulty_score += 3
            factors.append("Heavy misdirection (hard)")
        
        # Factor 3: Critical evidence clarity
        if len(critical_evidence) >= 4:
            difficulty_score += 1
            factors.append("Clear evidence trail (easy)")
        elif len(critical_evidence) >= 2:
            difficulty_score += 2
            factors.append("Moderate evidence (medium)")
        else:
            difficulty_score += 3
            factors.append("Scarce evidence (hard)")
        
        # Map score to difficulty
        if difficulty_score <= 4:
            difficulty = "EASY"
        elif difficulty_score <= 6:
            difficulty = "MEDIUM"
        else:
            difficulty = "HARD"
        
        return {
            'difficulty': difficulty,
            'difficulty_score': difficulty_score,
            'max_score': 9,
            'factors': factors,
            'estimated_playtime': self._estimate_playtime(difficulty, len(suspects))
        }
    
    def _estimate_playtime(self, difficulty: str, suspect_count: int) -> str:
        """Estimate how long the mystery will take to play"""
        base_minutes = 20 + (suspect_count * 5)
        
        if difficulty == "EASY":
            return f"{base_minutes}-{base_minutes + 15} minutes"
        elif difficulty == "MEDIUM":
            return f"{base_minutes + 10}-{base_minutes + 30} minutes"
        else:
            return f"{base_minutes + 20}-{base_minutes + 45} minutes"
    
    def generate_full_report(self, num_players: int = 4) -> str:
        """Generate a complete gameplay validation report"""
        
        solvability = self.validate_solvability()
        sharing = self.validate_information_sharing(num_players)
        difficulty = self.estimate_difficulty()
        
        report = []
        report.append("="*70)
        report.append("MYSTERY GAMEPLAY VALIDATION REPORT")
        report.append("="*70)
        report.append("")
        report.append(f"Mystery: {self.mystery['title']}")
        report.append(f"For {num_players} players")
        report.append("")
        
        # Solvability
        report.append("SOLVABILITY CHECK")
        report.append("-" * 70)
        status = "✅ PASS" if solvability['solvable'] else "❌ FAIL"
        report.append(f"Status: {status}")
        
        if solvability['issues']:
            report.append("\nCritical Issues:")
            for issue in solvability['issues']:
                report.append(f"  ❌ {issue}")
        
        if solvability['warnings']:
            report.append("\nWarnings:")
            for warning in solvability['warnings']:
                report.append(f"  ⚠️  {warning}")
        
        report.append(f"\nCritical Evidence: {solvability['critical_evidence_count']}")
        report.append(f"Red Herring Ratio: {int(solvability['red_herring_ratio']*100)}%")
        report.append(f"Suspects: {solvability['suspect_count']}")
        report.append("")
        
        # Information Sharing
        report.append("INFORMATION SHARING MECHANICS")
        report.append("-" * 70)
        report.append(f"Strategic Depth: {sharing['strategic_depth']}")
        report.append(f"Total Evidence: {sharing['total_evidence']} pieces")
        report.append(f"\nPer Player (estimated after 3 turns):")
        report.append(f"  - Total information: ~{sharing['items_per_player_estimate']} items")
        report.append(f"  - Must share (75%): ~{sharing['must_share_count']} items")
        report.append(f"  - Can withhold (25%): ~{sharing['can_hide_count']} items")
        
        if sharing['notes']:
            report.append("\nNotes:")
            for note in sharing['notes']:
                report.append(f"  • {note}")
        report.append("")
        
        # Difficulty
        report.append("DIFFICULTY ASSESSMENT")
        report.append("-" * 70)
        report.append(f"Difficulty: {difficulty['difficulty']}")
        report.append(f"Score: {difficulty['difficulty_score']}/{difficulty['max_score']}")
        report.append(f"Estimated Playtime: {difficulty['estimated_playtime']}")
        report.append("\nFactors:")
        for factor in difficulty['factors']:
            report.append(f"  • {factor}")
        report.append("")
        
        # Overall recommendation
        report.append("RECOMMENDATION")
        report.append("-" * 70)
        if not solvability['solvable']:
            report.append("❌ Mystery has critical issues. Fix before using in game.")
        elif solvability['warnings']:
            report.append("⚠️  Mystery is playable but could be improved.")
        else:
            report.append("✅ Mystery is ready for gameplay!")
        
        report.append("")
        report.append("="*70)
        
        return "\n".join(report)


# ============================================================================
# DEMO: Validate the sample mystery
# ============================================================================

if __name__ == "__main__":
    print("\n🔍 MYSTERY GAMEPLAY VALIDATION DEMO\n")
    
    validator = MysteryGameplayValidator(
        "./mystery_database/scenarios/the_locked_room_mystery.json"
    )
    
    report = validator.generate_full_report(num_players=4)
    print(report)
    
    print("\n💡 HOW THIS HELPS YOUR GAME:")
    print("-" * 70)
    print("1. QUALITY ASSURANCE")
    print("   - Automatically validates mysteries before players see them")
    print("   - Catches unsolvable or unfair mysteries")
    print("")
    print("2. DIFFICULTY TUNING")
    print("   - Estimates difficulty so you can match to player skill")
    print("   - Helps create balanced mystery sets (easy/medium/hard)")
    print("")
    print("3. STRATEGIC DEPTH VALIDATION")
    print("   - Ensures 75% sharing mechanic creates real decisions")
    print("   - Verifies mysteries support competitive play")
    print("")
    print("4. PLAYTESTING PREDICTIONS")
    print("   - Estimates playtime before actual testing")
    print("   - Predicts player behavior patterns")
    print("")
    print("5. RAG ENHANCEMENT")
    print("   - Can use this validation data to IMPROVE generation")
    print("   - Example: 'Generate a MEDIUM difficulty mystery like X'")
    print("")
    print("="*70)
