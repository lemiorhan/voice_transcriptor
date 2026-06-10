# Per-recording project folders + language selection

**Date:** 2026-06-10
**File affected:** `meeting-transcriptor.py` (plus new `config.json` at runtime)

## Goal

Stop appending every transcription to a single shared file. Instead, give each
recording its own self-contained project folder, and let the user pick the
transcription language (Turkish or English), remembered across runs.

## Behavior

### Config

A `config.json` file lives next to the script and stores:

```json
{
  "language": "tr",
  "base_path": "/abs/path/to/recordings",
  "input_device": "MX Brio",
  "capture_system_audio": true
}
```

- Created on first run, updated whenever the user changes language, base path,
  mic device, or the system-audio capture toggle.
- `language` is one of `"tr"` or `"en"`.
- `input_device` is the mic device **name** (not index), since indices change
  between sessions as devices connect/disconnect.
- `capture_system_audio` is a bool. When false/absent, recording is mic-only.

### Startup flow

Every launch prompts for each setting **with the saved value pre-filled as the
default** — pressing Enter keeps the last choice, typing/selecting changes it.

1. Load `config.json` if present.
2. **Confirm base project folder.** Default = saved path, or `./recordings` on
   first run. Created if missing. Saved to config.
3. **Transcription language.** Default = saved language (or `tr`). Saved to config.
4. **Mic device.** List all input-capable devices (physical mics plus
   virtual/app-audio devices like Zoom/Teams); default = saved device's position
   (or the first device if the saved one is gone). Saved by name.
5. **System audio capture — optional (on/off).** A yes/no prompt; default = saved
   choice. When on, the app records mic + the whole system audio mix together via
   a Core Audio process tap (see below). Saved as bool `capture_system_audio`.

### Input device (mic)

- If a device cannot be opened (e.g. unsupported sample rate), `record_audio`
  reports the error and returns `False` so the user can pick another via the menu.
- Menu gains `d` (mic) and `s` (system-audio on/off) options.

### Mic + system audio (record both) — Core Audio process taps

System (speaker) audio is captured with a **macOS Core Audio process tap**, not
BlackHole. The tap (`CATapDescription(stereoGlobalTapButExcludeProcesses:)` with
`muteBehavior = .unmuted`) captures the whole system mix **while playback stays
audible** — so the user keeps hearing audio and no BlackHole / Multi-Output / output
rerouting is required. Requires macOS 14.4+.

**Swift helper** (`mac_audio_tap/system_audio_tap.swift`): creates the tap, a
**private aggregate device** containing the tap (`kAudioAggregateDeviceTapListKey`;
note `…TapAutoStartKey` MUST be false — true deadlocks
`AudioDeviceCreateIOProcIDWithBlock`), an IOProc, and streams the tap's audio to
stdout as raw little-endian **float32** PCM. Protocol: first stdout line is a text
header `samplerate=<int> channels=<int> format=f32le\n`, then continuous frames
until SIGTERM. It is compiled on first use via `swiftc` (cached as
`mac_audio_tap/system_audio_tap`, gitignored); the source is committed.

**Python side:**
- `build_tap_binary()` compiles the helper if the binary is missing/stale; raises
  if `swiftc` is absent or compilation fails.
- `TapRecorder` spawns the helper, reads the header (with a 10 s timeout → assume
  permission issue), then accumulates float32 PCM on a reader thread; `stop()`
  SIGTERMs the process; `result()` returns the float32 array + rate.
- `DeviceRecorder` wraps a `sd.InputStream` for the mic at its **native rate**
  (not forced 16 kHz) with `CoreAudioSettings(change_device_parameters=False)` so
  PortAudio never changes a device's global sample rate (this also keeps the prior
  "don't interrupt playback" fix for any device).
- `record_audio(filepath, mic_device, capture_system=False, target_fs=16000)`
  starts a `DeviceRecorder` (mic) and, if enabled, a `TapRecorder` concurrently.
  The mic is **critical** (failure aborts the recording); the tap is **best-effort**
  (build/permission failure → warn and continue mic-only).

#### Native-rate capture → resample → mix

- Each source is captured at its own native rate (mic 48000/44100…, tap 48000).
- `resample_to_target` converts each (int16 *or* float32, mono/stereo) to 16 kHz
  mono: to float, average channels, and if native ≠ 16000 resample with
  `torchaudio.functional.resample` using a Kaiser anti-aliasing filter
  (`lowpass_filter_width=64, rolloff=0.945, sinc_interp_kaiser, beta≈14.77`,
  ~−89 dB above the 8 kHz Nyquist; naive linear interpolation would alias into the
  speech band). float→int16 with rounding + clipping. No-op when already 16 kHz.
- `mix_to_mono` trims all sources to the shortest (independent clocks drift), sums
  as int32, peak-limits. Written as one **16 kHz mono** WAV (Whisper's input).
- `torch`/`torchaudio` are imported lazily inside `resample_to_target`.
- Purpose is transcription, not production audio: minor inter-stream drift is fine.
- First system-audio use prompts for the macOS "System Audio Recording" (TCC)
  permission; if denied, the tap fails to start and recording continues mic-only.

### Per recording

- Create a timestamped subfolder `<base>/YYYY-MM-DD_HH-MM-SS/`.
- Record audio and save as `audio.wav` inside that subfolder.
- Transcribe with the model chosen by the selected language (see "Models").
- Save the transcription to `transcription.txt` inside the same subfolder.

## Models (per language)

`distil-large-v3` is English-only, so each language uses a different model and
runtime:

- **Turkish (`tr`):** `selimc/whisper-large-v3-turbo-turkish` via the Hugging
  Face `transformers` pipeline (`generate_kwargs={"language": "turkish",
  "task": "transcribe"}`). Downloaded/cached by `transformers` on first use.
- **English (`en`):** `ggml-distil-large-v3` via whisper.cpp (`pywhispercpp`).
  The `.bin` (~1.5 GB) is fetched from `distil-whisper/distil-large-v3-ggml`
  with `huggingface_hub.hf_hub_download` and cached on first use.

Device selection picks CUDA → Apple Silicon (MPS/Metal) → CPU automatically.
(The previous code hardcoded `device=0`/CUDA, which fails on non-CUDA machines.)
Each model is lazy-loaded once and cached for the session.

### Menu after each recording (replaces the y/n prompt)

- `[Enter]` — start a new recording
- `l` — change language (toggle/select tr or en); updates config immediately
- `d` — change mic (input) device; updates config immediately
- `s` — toggle system-audio capture (Core Audio tap) on/off; updates config
- `q` — quit

## Code structure

New/changed helpers in `meeting-transcriptor.py`:

- `load_config()` / `save_config(cfg)` — read/write `config.json`.
- `confirm_base_path(cfg)` — prompt and persist the base folder.
- `select_language(cfg)` — prompt for tr/en and persist; returns code.
- `lang_name(code)` — map `tr`→`turkish`, `en`→`english` for Whisper.
- `record_audio(filepath, fs)` — now takes a full output path.
- `transcribe_audio(filepath, language_name)` — now takes the language.
- `main()` — rewired for startup flow + per-recording subfolder + menu.

The old top-level `recorded_audio.wav` / `transcription.txt` are no longer
written. Existing untracked copies are left as-is.

## Testing

The interactive audio/Whisper paths are not unit-testable here. The pure helpers
are: config load/save round-trip, default handling when config is missing, and
`lang_name` mapping. These get covered with a small test using a temp dir.

## Out of scope

- No translation to a non-English target (Whisper translates reliably only to
  English).
- No changes to `mp4-transcriptor.py`.
- Distil-Whisper is English-only; Turkish quality relies on the separate
  `selimc` model, not on `distil-large-v3`.
