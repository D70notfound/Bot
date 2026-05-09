import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bot.game_state import GameState, Entity, BBox
from bot.strategy import ShowdownStrategy

CONFIG = {
    "strategy": {
        "poison_safety_margin_px": 60,
        "engage_min_hp_pct": 0.35,
        "collect_cube_radius_px": 200,
        "projectile_dodge_radius_px": 80,
        "shoot_range_px": 350,
        "super_min_enemies_nearby": 2,
    }
}


def make_entity(cls, cx, cy, w=40, h=40, conf=0.9) -> Entity:
    return Entity(bbox=BBox(cx=cx, cy=cy, w=w, h=h, confidence=conf), cls=cls)


def base_state(**kwargs) -> GameState:
    state = GameState()
    state.player = make_entity("player", 320, 240)
    for k, v in kwargs.items():
        setattr(state, k, v)
    return state


@pytest.fixture
def strategy():
    return ShowdownStrategy(CONFIG)


# Priority 1: dodge projectiles
def test_dodge_projectile_in_range(strategy):
    proj = make_entity("projectile", 340, 250)  # ~22px from player
    state = base_state(projectiles=[proj])
    action = strategy.decide(state)
    assert action.reason == "dodge_projectile"
    assert action.move_target is not None
    assert action.shoot_target is None


def test_no_dodge_when_projectile_far(strategy):
    proj = make_entity("projectile", 600, 500)  # far away
    state = base_state(projectiles=[proj])
    action = strategy.decide(state)
    assert action.reason != "dodge_projectile"


# Priority 2: flee poison
def test_flee_poison_when_inside(strategy):
    # Poison at (320, 240) with size 300x300 — player is at center
    poison = make_entity("poison", 320, 240, w=300, h=300)
    state = base_state(poison_zones=[poison])
    action = strategy.decide(state)
    assert action.reason == "flee_poison"
    assert action.move_target is not None


def test_no_flee_poison_when_outside(strategy):
    # Poison far away
    poison = make_entity("poison", 10, 10, w=20, h=20)
    state = base_state(poison_zones=[poison])
    action = strategy.decide(state)
    assert action.reason != "flee_poison"


# Priority 3: collect power cube
def test_collect_nearby_cube(strategy):
    cube = make_entity("power_cube", 380, 260)  # ~65px away, within 200 radius
    state = base_state(power_cubes=[cube])
    action = strategy.decide(state)
    assert action.reason in ("collect_cube", "collect_cube_shoot_enemy")
    assert action.move_target == pytest.approx((380.0, 260.0), abs=1)


def test_no_collect_distant_cube(strategy):
    cube = make_entity("power_cube", 700, 700)  # far
    state = base_state(power_cubes=[cube])
    action = strategy.decide(state)
    assert action.reason != "collect_cube"


# Priority 4: engage enemy
def test_shoot_enemy_in_range(strategy):
    enemy = make_entity("enemy", 500, 300)  # ~197px from player, within 350
    state = base_state(enemies=[enemy])
    action = strategy.decide(state)
    assert action.reason == "shoot_enemy"
    assert action.shoot_target == pytest.approx((500.0, 300.0), abs=1)
    assert action.stop_moving is True


def test_chase_enemy_out_of_range(strategy):
    enemy = make_entity("enemy", 800, 700)  # far away
    state = base_state(enemies=[enemy])
    action = strategy.decide(state)
    assert action.reason == "chase_enemy"
    assert action.move_target == pytest.approx((800.0, 700.0), abs=1)


# Priority 5: explore fallback
def test_explore_to_box_when_nothing(strategy):
    box = make_entity("box", 450, 400)
    state = base_state(boxes=[box])
    action = strategy.decide(state)
    assert action.reason == "explore_to_box"


def test_explore_to_center_when_empty(strategy):
    strategy.set_screen_region({"left": 0, "top": 0, "width": 640, "height": 480})
    state = base_state()
    action = strategy.decide(state)
    assert action.reason == "explore_to_center"
    assert action.move_target == pytest.approx((320.0, 240.0), abs=1)


# HP estimation
def test_low_hp_skips_engagement(strategy):
    # live_bar width much smaller than player width → low HP
    player_entity = make_entity("player", 320, 240, w=40, h=50)
    live_bar = make_entity("live_bar", 320, 215, w=10, h=6)  # 10/40 = 25% HP
    enemy = make_entity("enemy", 400, 280)
    state = GameState()
    state.player = player_entity
    state.enemies = [enemy]
    state.live_bars = [live_bar]
    action = strategy.decide(state)
    # HP 25% < 35% threshold → should not engage
    assert action.reason != "shoot_enemy"
    assert action.reason != "chase_enemy"
