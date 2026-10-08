"""Offline OCR (RapidOCR / PP-OCR ONNX models) and offline text-to-speech (Piper neural TTS)."""
import time
import wave


class Reader:
    def __init__(self):
        from rapidocr_onnxruntime import RapidOCR
        self.engine = RapidOCR()

    def read(self, bgr, min_score=0.5):
        t0 = time.perf_counter()
        result, _ = self.engine(bgr)
        dt = (time.perf_counter() - t0) * 1e3
        boxes = []
        for box, text, score in (result or []):
            if float(score) >= min_score:
                ys = [p[1] for p in box]
                boxes.append({'cy': (min(ys) + max(ys)) / 2, 'h': max(ys) - min(ys), 'x': min(p[0] for p in box),
                              'text': text})
        # group boxes into text lines (vertical centres closer than half a box height), then read left to right
        boxes.sort(key=lambda b: b['cy'])
        rows = []
        for b in boxes:
            if rows and abs(b['cy'] - rows[-1][-1]['cy']) < 0.5 * max(b['h'], rows[-1][-1]['h']):
                rows[-1].append(b)
            else:
                rows.append([b])
        lines = [' '.join(b['text'] for b in sorted(r, key=lambda b: b['x'])) for r in rows]
        return ' '.join(lines), dt


class Speaker:
    def __init__(self, model_path):
        from piper import PiperVoice
        self.voice = PiperVoice.load(model_path)

    def synth(self, text, wav_path):
        """Writes a WAV file; returns (synthesis time ms, audio length s)."""
        t0 = time.perf_counter()
        with wave.open(wav_path, 'wb') as wf:
            if hasattr(self.voice, 'synthesize_wav'):
                self.voice.synthesize_wav(text, wf)
            else:
                self.voice.synthesize(text, wf)
        dt = (time.perf_counter() - t0) * 1e3
        with wave.open(wav_path, 'rb') as wf:
            dur = wf.getnframes() / float(wf.getframerate())
        return dt, dur
