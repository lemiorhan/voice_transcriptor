# NOTICE

Audiocript
Copyright (c) 2026 Audiocript contributors

This product is licensed under the MIT License (see [LICENSE](LICENSE)).

## Based on prior work

Audiocript is a derivative of **voice_transcriptor** by **Semih Şahan**,
used and distributed under the terms of its MIT License.

- Original project: https://github.com/semihshn/voice_transcriptor
- Original copyright: Copyright (c) 2025 Semih Şahan

The original copyright notice and MIT permission notice are retained in
[LICENSE](LICENSE), as required by that license.

## Third-party components

Audiocript downloads and/or builds on the following components at runtime. They
are not redistributed in this repository; they are fetched from their sources and
remain under their own licenses.

### Transcription models
- `selimc/whisper-large-v3-turbo-turkish` — Turkish model, a fine-tune of
  OpenAI Whisper. https://huggingface.co/selimc/whisper-large-v3-turbo-turkish
- `distil-whisper/distil-large-v3` (ggml build) — English model.
  https://huggingface.co/distil-whisper/distil-large-v3-ggml
- OpenAI Whisper. https://github.com/openai/whisper (MIT)
- Distil-Whisper. https://github.com/huggingface/distil-whisper (MIT)

### Python libraries
- PyTorch / torchaudio — https://pytorch.org (BSD-3-Clause)
- Hugging Face Transformers / huggingface_hub — https://github.com/huggingface (Apache-2.0)
- pywhispercpp (whisper.cpp bindings) — https://github.com/absadiki/pywhispercpp (MIT)
- whisper.cpp — https://github.com/ggerganov/whisper.cpp (MIT)
- Rich — https://github.com/Textualize/rich (MIT)
- sounddevice (PortAudio bindings) — https://python-sounddevice.readthedocs.io (MIT)
- pynput — https://github.com/moses-palmer/pynput (LGPL-3.0)
- NumPy — https://numpy.org (BSD-3-Clause)

### System tools (used if present, not bundled)
- ffmpeg — https://ffmpeg.org (LGPL/GPL depending on build)
- Apple Core Audio / AudioToolbox and the Swift toolchain (macOS / Xcode Command Line Tools)

This NOTICE is provided for attribution and convenience. The license terms in
[LICENSE](LICENSE) govern your use of Audiocript itself; third-party components
are governed by their respective licenses.
