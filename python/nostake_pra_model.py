# nostake_pra_model.py
#
# NoStake PRA v1
# --------------
# This module implements custom PRA projection + hit probability model.
#
# The idea:
#   mu = B * F_match * F_min * F_usage
#
#   where:
#     B        = blended baseline PRA (season + last 5)
#     F_match  = matchup factor (defense + pace tiers)
#     F_min    = minutes factor (projected minutes vs season minutes)
#     F_usage  = usage/injury factor (key scorer out, key defender out)
#
# Then we assume PRA ~ Normal(mu, sigma^2) and convert a line into
# probabilities for over/under using the normal CDF.

from dataclasses import dataclass
from math import erf, sqrt
from typing import Optional, Dict


# --------- Basic math helpers ---------

def normal_cdf(z: float) -> float:
    """
    Standard normal CDF Φ(z).
    Uses math.erf so we don't depend on SciPy.
    """
    return 0.5 * (1.0 + erf(z / sqrt(2.0)))


# --------- Config ---------

@dataclass
class NoStakePRAConfig:
    """
    Tunable weights for the NoStake PRA model.
    You can tweak these later based on backtesting.
    """
    # Baseline blend: B = w_season * SPA + w_recent * RPA5
    weight_season: float = 0.6
    weight_recent: float = 0.4

    # Matchup factor:
    # F_match = 1 + defense_weight * T_def + pace_weight * T_pace
    #   T_def  = -1 (top 5 defense), 0 (middle), +1 (bottom 5 defense)
    #   T_pace = -1 (slow), 0 (middle), +1 (fast)
    defense_weight: float = 0.07  # 7% swing per defense tier
    pace_weight: float = 0.05     # 5% swing per pace tier

    # Usage factor:
    # F_usage = 1 + key_scorer_out_weight * key_scorer_out
    #              + opp_key_defender_weight * opp_key_defender_out
    key_scorer_out_weight: float = 0.08   # 8% PRA bump if major scorer teammate is out
    opp_defender_out_weight: float = 0.05 # 5% PRA bump if primary defender is out

    # Blowout handling (for minutes projection)
    blowout_spread_threshold: float = 10.0  # spread magnitude where we start to worry
    blowout_minutes_shave: float = 2.0      # minutes shaved off in big blowout spots


# --------- Core components ---------

def compute_baseline_pra(
    spa: float,
    rpa5: float,
    cfg: NoStakePRAConfig
) -> float:
    """
    Baseline PRA:
        B = w_season * SPA + w_recent * RPA5

    spa  = season average PRA up to this game
    rpa5 = last-5-games average PRA (up to this game)
    """
    return cfg.weight_season * spa + cfg.weight_recent * rpa5


def compute_matchup_factor(
    t_def: int,
    t_pace: int,
    cfg: NoStakePRAConfig
) -> float:
    """
    Matchup factor based on defensive rating tier and pace tier.

    t_def:
        -1 = top 5 defense (tough)
         0 = middle of the pack
        +1 = bottom 5 defense (easy)

    t_pace:
        -1 = slow
         0 = average
        +1 = fast
    """
    return 1.0 + cfg.defense_weight * t_def + cfg.pace_weight * t_pace


def project_minutes(
    min_season: float,
    min_recent5: float,
    cfg: NoStakePRAConfig,
    *,
    minutes_cap: Optional[float] = None,
    spread_from_players_team_perspective: Optional[float] = None,
    is_players_team_favorite: Optional[bool] = None,
) -> float:
    """
    Projected minutes for the game.

    min_season  = season average minutes (up to this game)
    min_recent5 = last-5-games average minutes (up to this game)

    minutes_cap:
        If there's a known minutes restriction (e.g. 28 off injury),
        pass that here and we'll cap projection at that value.

    spread_from_players_team_perspective:
        Closing spread for this game from the player's team perspective.
        Example:
            -5.5 means player's team is favored by 5.5
            +7.0 means player's team is +7 underdog.

    is_players_team_favorite:
        True  if player's team is the favorite
        False if dog's side
        None  if you don't want to apply blowout logic

    Blowout logic:
        - If favored by >= blowout_spread_threshold (e.g. -10 or lower),
          shave blowout_minutes_shave minutes.
        - If huge dog (spread >= threshold) you can also shave minutes
          (garbage-time risk); that's optional and you can tweak later.
    """
    # Base blend of season + recent minutes
    min_raw = 0.5 * min_season + 0.5 * min_recent5
    min_proj = min_raw

    # Injury / ramp-up cap
    if minutes_cap is not None:
        min_proj = min(min_proj, minutes_cap)

    # Blowout handling
    if (
        spread_from_players_team_perspective is not None
        and is_players_team_favorite is not None
    ):
        s = spread_from_players_team_perspective
        # Player's team big favorite: risk they sit the 4th quarter
        if is_players_team_favorite and abs(s) >= cfg.blowout_spread_threshold:
            min_proj -= cfg.blowout_minutes_shave
        # Player's team big dog: risk of getting blown out and losing minutes
        elif (not is_players_team_favorite) and abs(s) >= cfg.blowout_spread_threshold:
            min_proj -= cfg.blowout_minutes_shave

    # Don't allow negative minutes
    return max(min_proj, 0.0)


def compute_minutes_factor(
    min_season: float,
    min_proj: float
) -> float:
    """
    Minutes factor:
        F_min = min_proj / min_season

    If min_season is zero (should never happen), we just fall back to 1.0.
    """
    if min_season <= 0:
        return 1.0
    return min_proj / min_season


def compute_usage_factor(
    key_scorer_out: bool,
    opp_key_defender_out: bool,
    cfg: NoStakePRAConfig
) -> float:
    """
    Usage factor based on teammate/defender injuries.

    key_scorer_out:
        True if a top-3 usage teammate is out (bumps usage for our guy).

    opp_key_defender_out:
        True if the primary on-ball defender (or main matchup) is out.
    """
    factor = 1.0
    if key_scorer_out:
        factor += cfg.key_scorer_out_weight
    if opp_key_defender_out:
        factor += cfg.opp_defender_out_weight
    return factor


# --------- High-level projection + probability ---------

def project_pra(
    *,
    spa: float,
    rpa5: float,
    min_season: float,
    min_recent5: float,
    t_def: int,
    t_pace: int,
    key_scorer_out: bool = False,
    opp_key_defender_out: bool = False,
    minutes_cap: Optional[float] = None,
    spread_from_players_team_perspective: Optional[float] = None,
    is_players_team_favorite: Optional[bool] = None,
    cfg: Optional[NoStakePRAConfig] = None,
) -> float:
    """
    Compute the projected PRA (mu) for a single player in a single game.

    All stats (SPA, RPA5, minutes) should be computed using only data
    available BEFORE this game (no peeking into the future).
    """
    if cfg is None:
        cfg = NoStakePRAConfig()

    # 1) Baseline PRA
    B = compute_baseline_pra(spa, rpa5, cfg)

    # 2) Matchup factor
    F_match = compute_matchup_factor(t_def, t_pace, cfg)

    # 3) Minutes factor
    min_proj = project_minutes(
        min_season=min_season,
        min_recent5=min_recent5,
        cfg=cfg,
        minutes_cap=minutes_cap,
        spread_from_players_team_perspective=spread_from_players_team_perspective,
        is_players_team_favorite=is_players_team_favorite,
    )
    F_min = compute_minutes_factor(min_season, min_proj)

    # 4) Usage / injury factor
    F_usage = compute_usage_factor(
        key_scorer_out=key_scorer_out,
        opp_key_defender_out=opp_key_defender_out,
        cfg=cfg,
    )

    mu = B * F_match * F_min * F_usage
    return mu


def pra_hit_probability(
    line: float,
    mu: float,
    sigma: float
) -> Dict[str, float]:
    """
    Given a line L, projected PRA mu, and standard deviation sigma,
    return:
        z       = (L - mu) / sigma
        p_over  = P(PRA >= L)
        p_under = P(PRA <  L)
    assuming PRA ~ Normal(mu, sigma^2).
    """
    if sigma <= 0:
        # Degenerate case; if sigma is 0, it's all projection
        p_over = 1.0 if mu >= line else 0.0
        p_under = 1.0 - p_over
        return {"z": 0.0, "p_over": p_over, "p_under": p_under}

    z = (line - mu) / sigma
    p_under = normal_cdf(z)
    p_over = 1.0 - p_under
    return {"z": z, "p_over": p_over, "p_under": p_under}


def evaluate_pra_prop(
    *,
    line: float,
    spa: float,
    rpa5: float,
    min_season: float,
    min_recent5: float,
    sigma: float,
    t_def: int,
    t_pace: int,
    key_scorer_out: bool = False,
    opp_key_defender_out: bool = False,
    minutes_cap: Optional[float] = None,
    spread_from_players_team_perspective: Optional[float] = None,
    is_players_team_favorite: Optional[bool] = None,
    cfg: Optional[NoStakePRAConfig] = None,
) -> Dict[str, float]:
    """
    Convenience wrapper to go from raw inputs straight to:
      - projected PRA (mu)
      - z-score vs line
      - probability over
      - probability under
    """
    mu = project_pra(
        spa=spa,
        rpa5=rpa5,
        min_season=min_season,
        min_recent5=min_recent5,
        t_def=t_def,
        t_pace=t_pace,
        key_scorer_out=key_scorer_out,
        opp_key_defender_out=opp_key_defender_out,
        minutes_cap=minutes_cap,
        spread_from_players_team_perspective=spread_from_players_team_perspective,
        is_players_team_favorite=is_players_team_favorite,
        cfg=cfg,
    )
    probs = pra_hit_probability(line=line, mu=mu, sigma=sigma)
    return {
        "mu": mu,
        "z": probs["z"],
        "p_over": probs["p_over"],
        "p_under": probs["p_under"],
    }


if __name__ == "__main__":
    # Tiny example with fake numbers just so you can sanity check.
    cfg = NoStakePRAConfig()

    # Example inputs (you'll replace these with real Devin Booker data)
    spa = 39.7           # season PRA avg
    rpa5 = 37.5          # last-5 PRA avg
    min_season = 35.5    # season minutes avg
    min_recent5 = 36.2   # last-5 minutes avg
    sigma = 6.5          # PRA std dev for this player (from game log)

    # Mavs example: elite defense (-1), fast pace (+1)
    t_def = -1
    t_pace = +1

    # Assume no key scorer or key defender injuries for now
    key_scorer_out = False
    opp_key_defender_out = False

    # Spread example: player's team is +3.5 dog at Dallas
    spread = +3.5
    is_favorite = False

    line = 35.5  # PRA prop line for this test

    result = evaluate_pra_prop(
        line=line,
        spa=spa,
        rpa5=rpa5,
        min_season=min_season,
        min_recent5=min_recent5,
        sigma=sigma,
        t_def=t_def,
        t_pace=t_pace,
        key_scorer_out=key_scorer_out,
        opp_key_defender_out=opp_key_defender_out,
        spread_from_players_team_perspective=spread,
        is_players_team_favorite=is_favorite,
        cfg=cfg,
    )

    print(f"Projected PRA (mu): {result['mu']:.2f}")
    print(f"Line: {line}")
    print(f"Z-score: {result['z']:.2f}")
    print(f"P(OVER {line}):  {result['p_over']:.3f}")
    print(f"P(UNDER {line}): {result['p_under']:.3f}")