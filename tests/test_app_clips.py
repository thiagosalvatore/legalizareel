import pytest

import app_clips


def test_scene_time_counts_from_the_clips_media_start(tmp_path):
    (tmp_path / "compositions").mkdir()
    (tmp_path / "compositions" / "darf.html").write_text('<video src="x.mp4" data-media-start="8.4"></video>')

    assert app_clips.scene_time(tmp_path, "darf", 11.8) == 11.8 - 8.4


def test_cut_time_skips_what_the_cut_leaves_out():
    segments = [(5.6, 7.6), (11.9, 22.8)]

    assert app_clips.cut_time(segments, 6.6) == pytest.approx(1.0)
    assert app_clips.cut_time(segments, 15.4) == pytest.approx(5.5)


def test_cut_time_refuses_a_moment_the_cut_leaves_out():
    with pytest.raises(ValueError):
        app_clips.cut_time([(5.6, 7.6), (11.9, 22.8)], 9.0)


def test_cut_points_are_where_each_segment_starts_in_the_cut():
    assert app_clips.cut_points([(7.0, 9.6), (15.0, 16.2), (22.6, 25.5)]) == pytest.approx((2.6, 3.8))
