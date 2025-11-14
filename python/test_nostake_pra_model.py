"""
Unit tests for nostake_pra_model.py

Covers:
  - Baseline PRA computation
  - Matchup factor calculations
  - Minutes projection (normal and blowout scenarios)
  - Minutes factor
  - Usage factor
  - Full projection pipeline
  - Probability conversion (normal, degenerate, and edge cases)
"""

import pytest
import math
from nostake_pra_model import (
    NoStakePRAConfig,
    normal_cdf,
    compute_baseline_pra,
    compute_matchup_factor,
    project_minutes,
    compute_minutes_factor,
    compute_usage_factor,
    project_pra,
    pra_hit_probability,
    evaluate_pra_prop,
)


class TestNormalCDF:
    """Test the standard normal CDF helper."""

    def test_normal_cdf_zero(self):
        """CDF at z=0 should be 0.5."""
        assert abs(normal_cdf(0.0) - 0.5) < 1e-10

    def test_normal_cdf_positive(self):
        """CDF for positive z should be > 0.5."""
        assert 0.5 < normal_cdf(1.0) < 1.0
        assert normal_cdf(2.0) > normal_cdf(1.0)

    def test_normal_cdf_negative(self):
        """CDF for negative z should be < 0.5."""
        assert 0.0 < normal_cdf(-1.0) < 0.5
        assert normal_cdf(-1.0) == pytest.approx(1.0 - normal_cdf(1.0), rel=1e-10)

    def test_normal_cdf_extreme(self):
        """CDF at extreme values should approach 0 or 1."""
        assert normal_cdf(-5.0) < 0.0001
        assert normal_cdf(5.0) > 0.9999


class TestConfig:
    """Test the NoStakePRAConfig defaults."""

    def test_default_config(self):
        """Verify default config weights are sensible."""
        cfg = NoStakePRAConfig()
        assert cfg.weight_season == 0.6
        assert cfg.weight_recent == 0.4
        assert cfg.weight_season + cfg.weight_recent == 1.0
        assert cfg.defense_weight == 0.07
        assert cfg.pace_weight == 0.05


class TestBaselinePRA:
    """Test compute_baseline_pra."""

    def test_baseline_pra_equal_averages(self):
        """If SPA == RPA5, baseline should equal them."""
        cfg = NoStakePRAConfig()
        spa = 35.0
        rpa5 = 35.0
        result = compute_baseline_pra(spa, rpa5, cfg)
        assert result == pytest.approx(35.0)

    def test_baseline_pra_weighted_blend(self):
        """Baseline should blend with 0.6 season + 0.4 recent."""
        cfg = NoStakePRAConfig()
        spa = 40.0
        rpa5 = 30.0
        result = compute_baseline_pra(spa, rpa5, cfg)
        expected = 0.6 * 40.0 + 0.4 * 30.0  # 36.0
        assert result == pytest.approx(expected)

    def test_baseline_pra_zero_values(self):
        """Baseline should handle zero values."""
        cfg = NoStakePRAConfig()
        result = compute_baseline_pra(0.0, 0.0, cfg)
        assert result == pytest.approx(0.0)

    def test_baseline_pra_high_recency(self):
        """If recent PRA is much higher, baseline is pulled up."""
        cfg = NoStakePRAConfig()
        spa = 30.0
        rpa5 = 50.0
        result = compute_baseline_pra(spa, rpa5, cfg)
        expected = 0.6 * 30.0 + 0.4 * 50.0  # 38.0
        assert result == pytest.approx(expected)


class TestMatchupFactor:
    """Test compute_matchup_factor."""

    def test_matchup_factor_neutral(self):
        """Neutral defense and pace (0, 0) should give factor of 1.0."""
        cfg = NoStakePRAConfig()
        result = compute_matchup_factor(0, 0, cfg)
        assert result == pytest.approx(1.0)

    def test_matchup_factor_elite_defense(self):
        """Elite defense (-1) should reduce factor by defense_weight."""
        cfg = NoStakePRAConfig()
        result = compute_matchup_factor(-1, 0, cfg)
        expected = 1.0 - cfg.defense_weight  # 0.93
        assert result == pytest.approx(expected)

    def test_matchup_factor_weak_defense(self):
        """Weak defense (+1) should increase factor by defense_weight."""
        cfg = NoStakePRAConfig()
        result = compute_matchup_factor(1, 0, cfg)
        expected = 1.0 + cfg.defense_weight  # 1.07
        assert result == pytest.approx(expected)

    def test_matchup_factor_fast_pace(self):
        """Fast pace (+1) should increase factor by pace_weight."""
        cfg = NoStakePRAConfig()
        result = compute_matchup_factor(0, 1, cfg)
        expected = 1.0 + cfg.pace_weight  # 1.05
        assert result == pytest.approx(expected)

    def test_matchup_factor_slow_pace(self):
        """Slow pace (-1) should reduce factor by pace_weight."""
        cfg = NoStakePRAConfig()
        result = compute_matchup_factor(0, -1, cfg)
        expected = 1.0 - cfg.pace_weight  # 0.95
        assert result == pytest.approx(expected)

    def test_matchup_factor_combined(self):
        """Both factors should stack additively."""
        cfg = NoStakePRAConfig()
        result = compute_matchup_factor(-1, 1, cfg)
        expected = 1.0 - cfg.defense_weight + cfg.pace_weight  # 1.0 - 0.07 + 0.05 = 0.98
        assert result == pytest.approx(expected)


class TestMinutesProjection:
    """Test project_minutes."""

    def test_minutes_projection_baseline(self):
        """Baseline: average of season and recent."""
        cfg = NoStakePRAConfig()
        min_season = 34.0
        min_recent5 = 36.0
        result = project_minutes(min_season, min_recent5, cfg)
        expected = 0.5 * 34.0 + 0.5 * 36.0  # 35.0
        assert result == pytest.approx(expected)

    def test_minutes_projection_with_cap(self):
        """If minutes_cap is set, projection should be capped."""
        cfg = NoStakePRAConfig()
        min_season = 34.0
        min_recent5 = 36.0
        cap = 28.0  # Injury cap
        result = project_minutes(
            min_season, min_recent5, cfg, minutes_cap=cap
        )
        assert result == pytest.approx(cap)

    def test_minutes_projection_blowout_favorite(self):
        """If favored by >= 10 and is favorite, shave blowout_minutes_shave."""
        cfg = NoStakePRAConfig()
        min_season = 34.0
        min_recent5 = 36.0
        spread = -12.0  # Favorite by 12
        result = project_minutes(
            min_season,
            min_recent5,
            cfg,
            spread_from_players_team_perspective=spread,
            is_players_team_favorite=True,
        )
        expected = 0.5 * 34.0 + 0.5 * 36.0 - cfg.blowout_minutes_shave  # 35.0 - 2.0 = 33.0
        assert result == pytest.approx(expected)

    def test_minutes_projection_blowout_underdog(self):
        """If underdog by >= 10, shave blowout_minutes_shave."""
        cfg = NoStakePRAConfig()
        min_season = 34.0
        min_recent5 = 36.0
        spread = 12.0  # Underdog by 12
        result = project_minutes(
            min_season,
            min_recent5,
            cfg,
            spread_from_players_team_perspective=spread,
            is_players_team_favorite=False,
        )
        expected = 0.5 * 34.0 + 0.5 * 36.0 - cfg.blowout_minutes_shave  # 35.0 - 2.0 = 33.0
        assert result == pytest.approx(expected)

    def test_minutes_projection_no_blowout(self):
        """If spread is small, no blowout shaving."""
        cfg = NoStakePRAConfig()
        min_season = 34.0
        min_recent5 = 36.0
        spread = -5.0  # Favorite by 5 (below threshold of 10)
        result = project_minutes(
            min_season,
            min_recent5,
            cfg,
            spread_from_players_team_perspective=spread,
            is_players_team_favorite=True,
        )
        expected = 0.5 * 34.0 + 0.5 * 36.0  # 35.0 (no shaving)
        assert result == pytest.approx(expected)

    def test_minutes_projection_non_negative(self):
        """Minutes should never go negative."""
        cfg = NoStakePRAConfig()
        min_season = 1.0
        min_recent5 = 1.0
        # Force big blowout shave
        cfg.blowout_minutes_shave = 5.0
        result = project_minutes(
            min_season,
            min_recent5,
            cfg,
            spread_from_players_team_perspective=-20.0,
            is_players_team_favorite=True,
        )
        assert result >= 0.0


class TestMinutesFactor:
    """Test compute_minutes_factor."""

    def test_minutes_factor_equal(self):
        """If min_proj == min_season, factor should be 1.0."""
        result = compute_minutes_factor(30.0, 30.0)
        assert result == pytest.approx(1.0)

    def test_minutes_factor_increased(self):
        """If min_proj > min_season, factor > 1.0."""
        result = compute_minutes_factor(30.0, 32.0)
        expected = 32.0 / 30.0
        assert result == pytest.approx(expected)

    def test_minutes_factor_decreased(self):
        """If min_proj < min_season, factor < 1.0."""
        result = compute_minutes_factor(30.0, 28.0)
        expected = 28.0 / 30.0
        assert result == pytest.approx(expected)

    def test_minutes_factor_zero_season(self):
        """If min_season <= 0, fall back to 1.0."""
        result = compute_minutes_factor(0.0, 30.0)
        assert result == pytest.approx(1.0)


class TestUsageFactor:
    """Test compute_usage_factor."""

    def test_usage_factor_baseline(self):
        """No injuries should give factor of 1.0."""
        cfg = NoStakePRAConfig()
        result = compute_usage_factor(False, False, cfg)
        assert result == pytest.approx(1.0)

    def test_usage_factor_key_scorer_out(self):
        """Key scorer out should bump by key_scorer_out_weight."""
        cfg = NoStakePRAConfig()
        result = compute_usage_factor(True, False, cfg)
        expected = 1.0 + cfg.key_scorer_out_weight  # 1.08
        assert result == pytest.approx(expected)

    def test_usage_factor_defender_out(self):
        """Opponent key defender out should bump by opp_defender_out_weight."""
        cfg = NoStakePRAConfig()
        result = compute_usage_factor(False, True, cfg)
        expected = 1.0 + cfg.opp_defender_out_weight  # 1.05
        assert result == pytest.approx(expected)

    def test_usage_factor_both_out(self):
        """Both injuries should stack."""
        cfg = NoStakePRAConfig()
        result = compute_usage_factor(True, True, cfg)
        expected = 1.0 + cfg.key_scorer_out_weight + cfg.opp_defender_out_weight  # 1.13
        assert result == pytest.approx(expected)


class TestFullProjection:
    """Test project_pra (full pipeline)."""

    def test_projection_baseline_no_factors(self):
        """With neutral factors, projection should equal baseline."""
        cfg = NoStakePRAConfig()
        result = project_pra(
            spa=35.0,
            rpa5=35.0,
            min_season=35.0,
            min_recent5=35.0,
            t_def=0,
            t_pace=0,
            key_scorer_out=False,
            opp_key_defender_out=False,
            cfg=cfg,
        )
        # B = 35.0, F_match = 1.0, F_min = 1.0, F_usage = 1.0
        # mu = 35.0 * 1.0 * 1.0 * 1.0 = 35.0
        assert result == pytest.approx(35.0)

    def test_projection_with_matchup_boost(self):
        """Weak defense should boost projection."""
        cfg = NoStakePRAConfig()
        result = project_pra(
            spa=35.0,
            rpa5=35.0,
            min_season=35.0,
            min_recent5=35.0,
            t_def=1,  # Weak defense
            t_pace=0,
            cfg=cfg,
        )
        # B = 35.0, F_match = 1 + 0.07 = 1.07, F_min = 1.0, F_usage = 1.0
        # mu = 35.0 * 1.07 = 37.45
        expected = 35.0 * 1.07
        assert result == pytest.approx(expected)

    def test_projection_with_minutes_reduction(self):
        """Reduced minutes should lower projection."""
        cfg = NoStakePRAConfig()
        result = project_pra(
            spa=35.0,
            rpa5=35.0,
            min_season=35.0,
            min_recent5=30.0,  # Recent is lower
            t_def=0,
            t_pace=0,
            cfg=cfg,
        )
        # min_proj = 0.5 * 35 + 0.5 * 30 = 32.5
        # F_min = 32.5 / 35 = 0.9286
        # mu = 35.0 * 1.0 * 0.9286 * 1.0
        min_proj = 0.5 * 35.0 + 0.5 * 30.0
        f_min = min_proj / 35.0
        expected = 35.0 * f_min
        assert result == pytest.approx(expected)

    def test_projection_with_usage_boost(self):
        """Key scorer out should boost projection."""
        cfg = NoStakePRAConfig()
        result = project_pra(
            spa=35.0,
            rpa5=35.0,
            min_season=35.0,
            min_recent5=35.0,
            t_def=0,
            t_pace=0,
            key_scorer_out=True,
            cfg=cfg,
        )
        # mu = 35.0 * 1.0 * 1.0 * 1.08 = 37.8
        expected = 35.0 * (1.0 + cfg.key_scorer_out_weight)
        assert result == pytest.approx(expected)

    def test_projection_multiplicative_stacking(self):
        """All factors should multiply together."""
        cfg = NoStakePRAConfig()
        result = project_pra(
            spa=40.0,
            rpa5=40.0,
            min_season=35.0,
            min_recent5=35.0,
            t_def=1,  # +0.07
            t_pace=1,  # +0.05
            key_scorer_out=True,
            opp_key_defender_out=False,
            cfg=cfg,
        )
        # B = 40.0
        # F_match = 1 + 0.07 + 0.05 = 1.12
        # F_min = 1.0
        # F_usage = 1 + 0.08 = 1.08
        # mu = 40.0 * 1.12 * 1.0 * 1.08
        expected = 40.0 * 1.12 * 1.08
        assert result == pytest.approx(expected)


class TestProbabilityConversion:
    """Test pra_hit_probability."""

    def test_probability_line_equals_mu(self):
        """If line == mu, p_over should be ~0.5."""
        result = pra_hit_probability(line=35.0, mu=35.0, sigma=5.0)
        assert abs(result["z"]) < 1e-10
        assert abs(result["p_over"] - 0.5) < 0.01
        assert abs(result["p_under"] - 0.5) < 0.01

    def test_probability_line_above_mu(self):
        """If line > mu, p_over should be < 0.5."""
        result = pra_hit_probability(line=40.0, mu=35.0, sigma=5.0)
        assert result["z"] == pytest.approx(1.0)
        assert result["p_over"] < 0.5
        assert result["p_under"] > 0.5
        assert result["p_over"] + result["p_under"] == pytest.approx(1.0)

    def test_probability_line_below_mu(self):
        """If line < mu, p_over should be > 0.5."""
        result = pra_hit_probability(line=30.0, mu=35.0, sigma=5.0)
        assert result["z"] == pytest.approx(-1.0)
        assert result["p_over"] > 0.5
        assert result["p_under"] < 0.5

    def test_probability_large_sigma(self):
        """Large sigma (high uncertainty) should flatten probabilities."""
        result_small = pra_hit_probability(line=40.0, mu=35.0, sigma=1.0)
        result_large = pra_hit_probability(line=40.0, mu=35.0, sigma=10.0)
        # With smaller sigma, line is further away (higher z), so p_over is smaller
        assert result_small["p_over"] < result_large["p_over"]

    def test_probability_sigma_zero(self):
        """If sigma <= 0, use deterministic comparison."""
        # mu >= line
        result = pra_hit_probability(line=35.0, mu=36.0, sigma=0.0)
        assert result["p_over"] == pytest.approx(1.0)
        assert result["p_under"] == pytest.approx(0.0)

        # mu < line
        result = pra_hit_probability(line=37.0, mu=36.0, sigma=0.0)
        assert result["p_over"] == pytest.approx(0.0)
        assert result["p_under"] == pytest.approx(1.0)


class TestEvaluatePRAProp:
    """Test evaluate_pra_prop (convenience wrapper)."""

    def test_evaluate_pra_prop_standard(self):
        """Standard evaluation should return all fields."""
        result = evaluate_pra_prop(
            line=35.5,
            spa=35.0,
            rpa5=36.0,
            min_season=35.0,
            min_recent5=35.5,
            sigma=6.0,
            t_def=0,
            t_pace=0,
        )
        assert "mu" in result
        assert "z" in result
        assert "p_over" in result
        assert "p_under" in result
        assert result["p_over"] + result["p_under"] == pytest.approx(1.0)

    def test_evaluate_pra_prop_realistic_scenario(self):
        """Realistic NBA player scenario."""
        # Devin Booker-like: strong PRA, neutral matchup, projected over line
        result = evaluate_pra_prop(
            line=35.5,
            spa=37.2,
            rpa5=38.1,
            min_season=35.5,
            min_recent5=36.0,
            sigma=6.5,
            t_def=0,
            t_pace=0,
            key_scorer_out=False,
            opp_key_defender_out=False,
        )
        # mu should be close to ~37.5, well above 35.5
        assert result["mu"] > 35.5
        assert result["p_over"] > 0.5

    def test_evaluate_pra_prop_with_injuries(self):
        """Scenario with teammate out should boost PRA."""
        result_no_injury = evaluate_pra_prop(
            line=35.5,
            spa=35.0,
            rpa5=35.0,
            min_season=35.0,
            min_recent5=35.0,
            sigma=6.0,
            t_def=0,
            t_pace=0,
            key_scorer_out=False,
        )
        result_with_injury = evaluate_pra_prop(
            line=35.5,
            spa=35.0,
            rpa5=35.0,
            min_season=35.0,
            min_recent5=35.0,
            sigma=6.0,
            t_def=0,
            t_pace=0,
            key_scorer_out=True,
        )
        assert result_with_injury["mu"] > result_no_injury["mu"]
        assert result_with_injury["p_over"] > result_no_injury["p_over"]

    def test_evaluate_pra_prop_with_blowout(self):
        """Blowout scenario should reduce projected PRA."""
        result_no_spread = evaluate_pra_prop(
            line=35.0,
            spa=35.0,
            rpa5=35.0,
            min_season=35.0,
            min_recent5=35.0,
            sigma=6.0,
            t_def=0,
            t_pace=0,
        )
        result_blowout = evaluate_pra_prop(
            line=35.0,
            spa=35.0,
            rpa5=35.0,
            min_season=35.0,
            min_recent5=35.0,
            sigma=6.0,
            t_def=0,
            t_pace=0,
            spread_from_players_team_perspective=-15.0,
            is_players_team_favorite=True,
        )
        # Blowout scenario reduces minutes, which reduces mu
        assert result_blowout["mu"] < result_no_spread["mu"]

    def test_evaluate_pra_prop_custom_config(self):
        """Custom config should be respected."""
        custom_cfg = NoStakePRAConfig(
            weight_season=0.5,
            weight_recent=0.5,
            defense_weight=0.10,  # More aggressive
        )
        result = evaluate_pra_prop(
            line=35.5,
            spa=40.0,
            rpa5=30.0,
            min_season=35.0,
            min_recent5=35.0,
            sigma=6.0,
            t_def=-1,  # Elite defense
            t_pace=0,
            cfg=custom_cfg,
        )
        # With 0.5/0.5 blend, mu should be 35.0; defense at -1 with 0.10 weight gives 0.90
        # mu = 35.0 * 0.90 * 1.0 * 1.0 = 31.5
        expected = 35.0 * 0.90
        assert result["mu"] == pytest.approx(expected)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
