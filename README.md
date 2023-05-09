# michat

ChatGPTの出力を初音ミクやカゲプロのエネっぽい口調で音声出力するアプリケーション

## Requirement

* VOICEVOX core (Python bindings)
    - you can download from [github](https://github.com/VOICEVOX/voicevox_core/releases)
    - extract and install in the current directory
* ONNX Runtime
    - you can download from [github](https://github.com/microsoft/onnxruntime/releases)
    - extract and copy dynamic libraries to current directory
* Open Jtalk dictionary
    - you can download from [sourceforge](http://downloads.sourceforge.net/open-jtalk/)
    - extract and install in the current directory

### Versions

| software        | version |
|-----------------|---------|
| VOICEVOX core   |  0.14.2 |
| ONNX Runtime    |  1.13.1 |
| Open Jtalk dict |  8-1.11 |

See the version of other python packeges in `requirements.txt` or `pyproject.toml`.
In the container environment, `requirements.txt` is preferred.

## Usage

### CLI

```
$ python3 speak.py --help          
usage: speak.py [-h] [--file FILE] [--file-system FILE_SYSTEM] [-t MAX_TOKENS] [-s SPEAKER_ID]
                [-o OUTPUT] [-L LOG_FILE] [-l LOG_LEVEL]

speak.py

options:
  -h, --help            show this help message and exit
  --file FILE           message to submit to ChatGPT
  --file-system FILE_SYSTEM
                        system message for ChatGPT
  -t MAX_TOKENS, --max-tokens MAX_TOKENS
                        Maximum tokens of ChatGPT response
  -s SPEAKER_ID, --speaker-id SPEAKER_ID
                        Speaker ID for the VOICEVOX model
  -o OUTPUT, --output OUTPUT
                        wav output
  -L LOG_FILE, --log-file LOG_FILE
                        log output file
  -l LOG_LEVEL, --log-level LOG_LEVEL
                        logger level
```

### Web (local)

```
$ streamlit run michat/app.py
```
