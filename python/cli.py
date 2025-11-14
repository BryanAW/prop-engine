#!/usr/bin/env python3
"""
CLI script for the NoStake PRA model.

Usage (interactive):
    python3 cli.py

Usage (command-line arguments):
    python3 cli.py --spa 35.0 --rpa5 36.0 --min-season 35.0 --min-recent5 35.5 \\
                    --sigma 6.5 --line 35.5 --t-def 0 --t-pace 0

The script will compute and display:
  - Projected PRA (mu)
  - Z-score vs. the line
  - Probability of going OVER the line
  - Probability of going UNDER the line
"""

import argparse
import sys
from nostake_pra_model import evaluate_pra_prop, NoStakePRAConfig


def get_inputs_interactive():
    """
    Prompt the user for all required inputs interactively.
    """
    print("\n" + "=" * 60)
    print("NoStake PRA Model - Interactive CLI")
    print("=" * 60 + "\n")

    print("Enter player stats and game parameters:")
    print("(You can use decimals. Default in parentheses.)\n")

    # Baseline PRA stats
    spa = float(input("Season PRA average (SPA) [default: 35.0]: ") or 35.0)
    rpa5 = float(input("Last-5 PRA average (RPA5) [default: 36.0]: ") or 36.0)

    # Minutes
    min_season = float(
        input("Season minutes average [default: 35.0]: ") or 35.0
    )
    min_recent5 = float(
        input("Last-5 minutes average [default: 35.5]: ") or 35.5
    )

    # Matchup tiers
    print("\nMatchup tiers: -1 (elite/fast), 0 (neutral), +1 (weak/slow)")
    t_def = int(input("Defense tier (-1, 0, 1) [default: 0]: ") or 0)
    t_pace = int(input("Pace tier (-1, 0, 1) [default: 0]: ") or 0)

    # Volatility
    sigma = float(input("\nPRA standard deviation (sigma) [default: 6.5]: ") or 6.5)

    # Prop line
    line = float(input("Prop line to evaluate [default: 35.5]: ") or 35.5)

    # Optional flags
    print("\nOptional factors:")
    key_scorer_out = (
        input("Key teammate scorer out? (y/n) [default: n]: ").lower() == "y"
    )
    opp_defender_out = (
        input("Opponent key defender out? (y/n) [default: n]: ").lower() == "y"
    )

    return {
        "spa": spa,
        "rpa5": rpa5,
        "min_season": min_season,
        "min_recent5": min_recent5,
        "t_def": t_def,
        "t_pace": t_pace,
        "sigma": sigma,
        "line": line,
        "key_scorer_out": key_scorer_out,
        "opp_key_defender_out": opp_defender_out,
    }


def get_inputs_from_args(args):
    """
    Parse command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description="NoStake PRA Model CLI - Evaluate player props",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Interactive mode:
    python3 cli.py

  Command-line mode:
    python3 cli.py --spa 35.0 --rpa5 36.0 --min-season 35.0 --min-recent5 35.5 \\
                    --sigma 6.5 --line 35.5 --t-def 0 --t-pace 0
        """,
    )

    parser.add_argument(
        "--spa",
        type=float,
        default=35.0,
        help="Season PRA average (default: 35.0)",
    )
    parser.add_argument(
        "--rpa5",
        type=float,
        default=36.0,
        help="Last-5 PRA average (default: 36.0)",
    )
    parser.add_argument(
        "--min-season",
        type=float,
        default=35.0,
        help="Season minutes average (default: 35.0)",
    )
    parser.add_argument(
        "--min-recent5",
        type=float,
        default=35.5,
        help="Last-5 minutes average (default: 35.5)",
    )
    parser.add_argument(
        "--t-def",
        type=int,
        default=0,
        choices=[-1, 0, 1],
        help="Defense tier: -1 (elite), 0 (neutral), 1 (weak) (default: 0)",
    )
    parser.add_argument(
        "--t-pace",
        type=int,
        default=0,
        choices=[-1, 0, 1],
        help="Pace tier: -1 (slow), 0 (neutral), 1 (fast) (default: 0)",
    )
    parser.add_argument(
        "--sigma",
        type=float,
        default=6.5,
        help="PRA standard deviation (default: 6.5)",
    )
    parser.add_argument(
        "--line",
        type=float,
        default=35.5,
        help="Prop line to evaluate (default: 35.5)",
    )
    parser.add_argument(
        "--key-scorer-out",
        action="store_true",
        help="Key teammate scorer is out",
    )
    parser.add_argument(
        "--opp-defender-out",
        action="store_true",
        help="Opponent key defender is out",
    )

    parsed = parser.parse_args(args)

    return {
        "spa": parsed.spa,
        "rpa5": parsed.rpa5,
        "min_season": parsed.min_season,
        "min_recent5": parsed.min_recent5,
        "t_def": parsed.t_def,
        "t_pace": parsed.t_pace,
        "sigma": parsed.sigma,
        "line": parsed.line,
        "key_scorer_out": parsed.key_scorer_out,
        "opp_key_defender_out": parsed.opp_defender_out,
    }


def print_results(inputs, result):
    """
    Pretty-print the evaluation results.
    """
    print("\n" + "=" * 60)
    print("EVALUATION RESULTS")
    print("=" * 60 + "\n")

    print("Input Summary:")
    print(f"  Season PRA (SPA):        {inputs['spa']:.1f}")
    print(f"  Recent 5 PRA (RPA5):     {inputs['rpa5']:.1f}")
    print(f"  Season Minutes:          {inputs['min_season']:.1f}")
    print(f"  Recent 5 Minutes:        {inputs['min_recent5']:.1f}")
    print(f"  Defense Tier (t_def):    {inputs['t_def']:+d}")
    print(f"  Pace Tier (t_pace):      {inputs['t_pace']:+d}")
    print(f"  Volatility (sigma):      {inputs['sigma']:.2f}")
    print(f"  Prop Line:               {inputs['line']:.1f}")
    if inputs["key_scorer_out"]:
        print(f"  Key Teammate Out:        YES")
    if inputs["opp_key_defender_out"]:
        print(f"  Opp. Key Defender Out:   YES")

    print("\n" + "-" * 60)
    print("Projection Results:")
    print("-" * 60)
    print(f"  Projected PRA (μ):       {result['mu']:.2f}")
    print(f"  Line:                    {inputs['line']:.1f}")
    print(f"  Z-Score:                 {result['z']:+.3f}")

    print("\n" + "-" * 60)
    print("Hit Probabilities:")
    print("-" * 60)
    print(f"  P(OVER {inputs['line']:.1f}):       {result['p_over']:.1%}")
    print(f"  P(UNDER {inputs['line']:.1f}):      {result['p_under']:.1%}")

    # Quick recommendation (just for context; not actual advice)
    print("\n" + "-" * 60)
    if result["p_over"] > 0.55:
        recommendation = "OVER lean (but always do your own research!)"
    elif result["p_under"] > 0.55:
        recommendation = "UNDER lean (but always do your own research!)"
    else:
        recommendation = "Near a pick (very balanced)"

    print(f"  Rough Take:              {recommendation}")
    print("=" * 60 + "\n")


def main():
    """
    Main entry point for the CLI.
    """
    # If arguments are provided, use them; otherwise go interactive
    if len(sys.argv) > 1:
        inputs = get_inputs_from_args(sys.argv[1:])
    else:
        inputs = get_inputs_interactive()

    # Evaluate the prop
    try:
        result = evaluate_pra_prop(
            line=inputs["line"],
            spa=inputs["spa"],
            rpa5=inputs["rpa5"],
            min_season=inputs["min_season"],
            min_recent5=inputs["min_recent5"],
            sigma=inputs["sigma"],
            t_def=inputs["t_def"],
            t_pace=inputs["t_pace"],
            key_scorer_out=inputs["key_scorer_out"],
            opp_key_defender_out=inputs["opp_key_defender_out"],
        )

        print_results(inputs, result)

    except ValueError as e:
        print(f"\nError: Invalid input. {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
