# Music Trainer - AI-Powered Practice Bot

An intelligent music practice companion that helps musicians develop their ear and repertoire through interactive call-and-response sessions.

## Vision

The ultimate goal is to create a practice bot that can learn from recordings of specific musical styles (genres, artists, albums) and teach students phrase-by-phrase through call-and-response practice. Imagine having a clone of Miles Davis in your living room, teaching you modal jazz one phrase at a time, adapting to your skill level in real-time.

## Current MVP Scope

This initial version focuses on core functionality with a single monophonic instrument:

### Features
- **MIDI Input**: Connect your USB MIDI controller for real-time interaction
- **Call-and-Response Training**: Bot plays a phrase, you play it back
- **Intelligent Evaluation**: Assessment of pitch accuracy and timing
- **Adaptive Difficulty**: Automatic adjustment based on your performance
- **Visual Feedback**: See the target phrase and your attempts
- **Curated Phrase Library**: Starting with a focused musical style

### Technical Stack
- **Python**: Core application language
- **MIDI**: `python-rtmidi` for USB MIDI controller input
- **Audio**: `sounddevice` + `numpy` for audio synthesis and playback
- **Music Theory**: `music21` for musical concepts and notation
- **GUI**: `tkinter` for cross-platform desktop interface
- **Data**: JSON/SQLite for phrase storage and user progress

## Getting Started

### Prerequisites
- Python 3.8+
- USB MIDI controller
- Audio output device (speakers/headphones)

### Installation
```bash
# Clone the repository
git clone https://github.com/eholly1/music_trainer.git
cd music_trainer

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

## How It Works

1. **Connect** your MIDI controller
2. **Select** difficulty level and musical style
3. **Listen** to the bot play a musical phrase
4. **Play back** the phrase on your controller
5. **Receive feedback** and adapt to the next challenge

The bot evaluates your performance across multiple dimensions:
- **Pitch Accuracy**: How close are your notes to the target?
- **Timing**: Are you playing with the correct rhythm?
- **Expression**: (Future) Dynamics and articulation

Based on your performance, the bot decides whether to:
- Repeat the current phrase for more practice
- Advance to a more complex phrase
- Simplify to build confidence

## Future Vision

- **Style Learning**: Ingest recordings to extract and generate phrases
- **Multi-dimensional Grading**: Rhythmic, tonal, and expressive evaluation
- **Expanded Instruments**: Support for polyphonic instruments and ensembles
- **Personalized Curriculum**: AI-driven lesson planning
- **Community Features**: Share progress and compete with other learners

## Contributing

This project is in active development. Contributions welcome!

## License

MIT License - see LICENSE file for details
