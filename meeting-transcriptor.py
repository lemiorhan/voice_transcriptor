import os
import sys
import json
import termios  # Unix tabanlı sistemlerde çalışır.
import wave
from datetime import datetime
from pathlib import Path
import numpy as np
import sounddevice as sd
import warnings
from pynput import keyboard
from transformers import pipeline
from rich.prompt import Prompt
from rich.console import Console
from rich.panel import Panel

# Uyarıları bastır (FutureWarning, DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Rich için konsol nesnesi oluşturuyoruz
console = Console()

# Yapılandırma dosyası, scriptin yanında saklanır.
CONFIG_PATH = Path(__file__).resolve().parent / "config.json"
DEFAULT_BASE_PATH = Path(__file__).resolve().parent / "recordings"

# Desteklenen diller: kod -> Whisper dil adı
LANGUAGES = {"tr": "turkish", "en": "english"}


def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')


def flush_stdin():
    """
    sys.stdin'de bekleyen (kalan) karakterleri temizler.
    Unix tabanlı sistemlerde termios.tcflush() kullanarak giriş tamponunu temizler.
    """
    try:
        termios.tcflush(sys.stdin, termios.TCIFLUSH)
    except Exception:
        pass


def load_config():
    """config.json'u okur. Dosya yoksa veya bozuksa boş bir sözlük döndürür."""
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        return cfg if isinstance(cfg, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_config(cfg):
    """Yapılandırmayı config.json'a yazar."""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def lang_name(code):
    """Dil kodunu ('tr'/'en') Whisper'ın beklediği dil adına çevirir."""
    return LANGUAGES.get(code, "turkish")


def confirm_base_path(cfg):
    """
    Proje klasörünün yolunu kullanıcıya onaylatır.
    Kaydedilmiş yol varsa onu, yoksa varsayılanı önerir. Klasörü oluşturur.
    """
    current = cfg.get("base_path") or str(DEFAULT_BASE_PATH)
    console.print(
        f"[bold blue]Kayıtların saklanacağı proje klasörü:[/bold blue] [cyan]{current}[/cyan]"
    )
    answer = Prompt.ask(
        "Bu yolu kullanmak için Enter'a basın veya yeni bir yol girin",
        default=current,
    )
    base_path = Path(os.path.expanduser(answer.strip() or current)).resolve()
    base_path.mkdir(parents=True, exist_ok=True)
    cfg["base_path"] = str(base_path)
    save_config(cfg)
    console.print(f"[green]Proje klasörü: {base_path}[/green]\n")
    return base_path


def select_language(cfg):
    """tr/en arasından dil seçtirir ve yapılandırmaya kaydeder. Dil kodunu döndürür."""
    choice = Prompt.ask(
        "Transkripsiyon dili seçin",
        choices=list(LANGUAGES.keys()),
        default=cfg.get("language", "tr"),
    )
    cfg["language"] = choice
    save_config(cfg)
    console.print(f"[green]Seçilen dil: {choice} ({lang_name(choice)})[/green]\n")
    return choice


def record_audio(filepath, fs=16000):
    clear_console()
    console.print(Panel("Ses Transkripsiyon Uygulamasına Hoşgeldiniz!", style="bold green"), justify="center")
    console.print("[bold blue]Kayda başlamak için 'Enter'a basın. Kayıt sırasında durdurmak için 'q' tuşuna basın.[/bold blue]\n")
    input()  # Kullanıcı Enter'a bastığında devam eder

    console.print("[bold yellow]Recording... (Press 'q' to stop)[/bold yellow]")
    audio_frames = []
    stop_flag = [False]  # Kayıt durdurulması için mutable bayrak

    def callback(indata, frames, time, status):
        if status:
            console.log(f"[red]{status}[/red]")
        audio_frames.append(indata.copy())

    def on_press(key):
        try:
            if key.char == 'q':
                console.print("[bold red]Recording stopped.[/bold red]")
                stop_flag[0] = True
                return False  # Dinleyiciyi durdur
        except AttributeError:
            pass

    listener = keyboard.Listener(on_press=on_press)
    listener.start()

    with sd.InputStream(samplerate=fs, channels=1, dtype='int16', callback=callback):
        while not stop_flag[0]:
            sd.sleep(100)

    listener.join()
    audio_data = np.concatenate(audio_frames, axis=0)

    with wave.open(str(filepath), 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit (2 byte)
        wf.setframerate(fs)
        wf.writeframes(audio_data.tobytes())
    console.print(f"[green]Audio saved to {filepath} ({len(audio_data)} samples)[/green]")


def transcribe_audio(filepath, language_name):
    console.print(f"[bold cyan]Transcribing audio ({language_name})...[/bold cyan]")
    pipe = pipeline("automatic-speech-recognition", model="openai/whisper-large-v3-turbo", device=0)
    transcription = pipe(
        str(filepath),
        return_timestamps=True,
        generate_kwargs={"language": language_name, "task": "transcribe"},
    )
    return transcription


def main():
    cfg = load_config()

    clear_console()
    console.print(Panel("Ses Transkripsiyon Uygulaması", style="bold magenta"), justify="center")

    # Başlangıç: proje klasörü ve dil seçimi
    base_path = confirm_base_path(cfg)
    language = cfg.get("language") or select_language(cfg)

    while True:
        # Her kayıt için zaman damgalı bir alt klasör (proje) oluştur.
        project_dir = base_path / datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        project_dir.mkdir(parents=True, exist_ok=True)

        audio_path = project_dir / "audio.wav"
        record_audio(audio_path)

        transcription = transcribe_audio(audio_path, lang_name(language))
        transcribed_text = transcription.get('text', '')
        console.print(Panel(f"[bold green]Transcription:[/bold green]\n{transcribed_text}", style="green"), justify="center")

        transcription_path = project_dir / "transcription.txt"
        with open(transcription_path, "w", encoding="utf-8") as file:
            file.write(transcribed_text + "\n")
        console.print(f"[bold green]Proje kaydedildi: {project_dir}[/bold green]\n")

        # Önceki kayıttan kalan karakterleri temizliyoruz.
        flush_stdin()

        # Kullanıcıya menüyü gösteriyoruz.
        console.print(
            f"[bold blue]Menü[/bold blue]  "
            f"[Enter] Yeni kayıt   "
            f"[l] Dili değiştir (mevcut: {language})   "
            f"[q] Çıkış"
        )
        try:
            response = Prompt.ask("Seçiminiz", default="")
        except Exception:
            response = ""
        choice = response.strip().lower()

        if choice == "q":
            console.print("[bold yellow]Çıkılıyor...[/bold yellow]")
            break
        elif choice == "l":
            language = select_language(cfg)
        # Diğer her durumda (Enter dahil) yeni kayda devam edilir.


if __name__ == "__main__":
    main()
