import app_clips


def test_scene_time_counts_from_the_clips_media_start(tmp_path):
    (tmp_path / "compositions").mkdir()
    (tmp_path / "compositions" / "darf.html").write_text('<video src="x.mp4" data-media-start="8.4"></video>')

    assert app_clips.scene_time(tmp_path, "darf", 11.8) == 11.8 - 8.4
