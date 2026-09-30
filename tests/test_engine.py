import engine


def test_hf_index_is_written_at_the_requested_size(tmp_path):
    scenes = [{"kind": "scene", "id": "hook", "dur": 2.0}]

    engine.write_hf_index(scenes, tmp_path, 2.0, {}, size=(1080, 1920))

    html = (tmp_path / "index.html").read_text()
    assert 'data-width="1080" data-height="1920"' in html
    assert 'content="width=1080, height=1920"' in html
    assert '"width": 1080, "height": 1920' in html


def test_kokoro_jobs_speak_brazilian_portuguese():
    jobs = [{"text": "Olá", "raw": "out.wav"}]

    spec = engine.kokoro_spec(jobs)

    assert spec == [{"text": "Olá", "voice": "pm_alex", "lang": "p", "speed": engine.KOKORO_SPEED, "out": "out.wav"}]


def test_sfx_lands_on_a_beat_of_the_final_scene_length():
    assert engine.sfx_offset(engine.Beat(0.5, delay=0.25), 6.0) == 3.25
    assert engine.sfx_offset(-0.5, 6.0) == 5.5
    assert engine.sfx_offset(1.2, 6.0) == 1.2
