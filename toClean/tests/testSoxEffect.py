import librosa
from pydub import AudioSegment
from pysndfx import AudioEffectsChain
import matplotlib.pyplot as plt
from matplotlib.mlab import window_hanning
import sounddevice
from utils.misc import pydub_audiosegment_to_float_array, float_array_to_pydub_audiosegment
from utils.effects import do_reverb_transform


def show_spectrogram(sound, idx, sample_rate, fft_length, fft_overlap):
  plt.specgram(x=sound, Fs=sample_rate,
               window=window_hanning,
               NFFT=fft_length,
               noverlap=fft_overlap, mode='magnitude', scale='dB')
  plt.draw()


class Tester:
  def __init__(self, original_sound, frame_rate, fft_length, fft_overlap):
    self.original_sound = original_sound
    self.frame_rate = frame_rate
    self.fft_length = fft_length
    self.fft_overlap = fft_overlap
    self.reverberance_test_values = list(range(0, 101, 10))
    self.reverberance_idx = 5
    self.damping_test_values = list(range(0, 101, 10))
    self.damping_idx = 5
    self.room_scale_test_values = list(range(0, 101, 10))
    self.room_scale_idx = 5
    self.stereo_depth_test_values = list(range(0, 101, 10))
    self.stereo_depth_idx = 5
    self.pre_delay_test_values = list(range(0, 501, 50))
    self.pre_delay_idx = 5
    self.wet_gain_test_values = list(range(0, 11, 1))
    self.wet_gain_idx = 0

    self.current_sound = None

    print("===================================================================")
    print("Press r for next Reverb -- Press R for previous Reverb")
    print("Press d for next Damping -- Press D for previous damping")
    print("Press x for next Stereo Depth -- Press X for previous Stereo Depth")
    print("Press p for next Pre delay -- Press P for previous Pre delay")
    print("Press w for next wet gain -- Press W for previous wet gain")
    print("Press m to play current sound -- Press M to stop current sound")

    plt.figure('Original scene')
    plt.specgram(x=self.original_sound, Fs=self.frame_rate,
                 window=window_hanning,
                 NFFT=self.fft_length,
                 noverlap=self.fft_overlap, mode='magnitude', scale='dB')

    plt.figure("With Reverb")
    self.show()

    plt.connect('key_press_event', self.change_image)
    plt.show()

  def change_image(self, event):

    if event.key == 'r' and self.reverberance_idx < len(self.reverberance_test_values) - 1 :
      self.reverberance_idx += 1
    elif event.key == 'R' and self.reverberance_idx > 0:
      self.reverberance_idx -= 1
    elif event.key == 'd' and self.damping_idx < len(self.damping_test_values) - 1 :
      self.damping_idx += 1
    elif event.key == 'D' and self.damping_idx > 0 :
      self.damping_idx -= 1
    elif event.key == 'x' and self.stereo_depth_idx < len(self.stereo_depth_test_values) - 1 :
      self.stereo_depth_idx += 1
    elif event.key == 'X' and self.stereo_depth_idx > 0 :
      self.stereo_depth_idx -= 1
    elif event.key == 'p' and self.pre_delay_idx < len(self.pre_delay_test_values) - 1 :
      self.pre_delay_idx += 1
    elif event.key == 'P' and self.pre_delay_idx > 0 :
      self.pre_delay_idx -= 1
    elif event.key == 'w' and self.wet_gain_idx < len(self.wet_gain_test_values) - 1 :
      self.wet_gain_idx += 1
    elif event.key == 'W' and self.wet_gain_idx > 0 :
      self.wet_gain_idx -= 1
    elif event.key == 'm':
      print("Playing sound")
      sounddevice.play(self.current_sound, self.frame_rate)
      return
    elif event.key == 'M':
      print("Sound stopped")
      sounddevice.stop()
      return
    else:
      return

    self.show()

  def show(self):
    self.current_sound = do_reverb_transform(self.original_sound,
                                            reverberance=self.reverberance_test_values[self.reverberance_idx],
                                            hf_damping=self.damping_test_values[self.damping_idx],
                                            stereo_depth=self.stereo_depth_test_values[self.stereo_depth_idx],
                                            pre_delay=self.pre_delay_test_values[self.pre_delay_idx],
                                            wet_gain=self.wet_gain_test_values[self.wet_gain_idx])

    plt.specgram(x=self.current_sound, Fs=self.frame_rate,
                 window=window_hanning,
                 NFFT=self.fft_length,
                 noverlap=self.fft_overlap, mode='magnitude', scale='dB')

    plt.title('Reverberance %d -- Hf Damping %d \nStereo Depth %d -- Pre delay %d\nWet gain %d' %
              (self.reverberance_test_values[self.reverberance_idx], self.damping_test_values[self.damping_idx],
               self.stereo_depth_test_values[self.stereo_depth_idx], self.pre_delay_test_values[self.pre_delay_idx],
               self.wet_gain_test_values[self.wet_gain_idx]))
    plt.draw()



def main():
  sound_filepath = "/NOBACKUP/jerome/datasets/AQA_V0.1/v0.2.1_10000_scenes/audio/test/AQA_test_000046.wav"
  fft_length = 1024
  fft_overlap = 512
  original_sound_audiosegment = AudioSegment.from_wav(sound_filepath)
  original_sound_float_array = pydub_audiosegment_to_float_array(original_sound_audiosegment, original_sound_audiosegment.frame_rate, original_sound_audiosegment.sample_width)
  test_back = float_array_to_pydub_audiosegment(original_sound_float_array, original_sound_audiosegment.frame_rate, original_sound_audiosegment.sample_width)
  original_sound, sample_rate = librosa.load(sound_filepath, sr=None)

  tester = Tester(original_sound_float_array, original_sound_audiosegment.frame_rate, fft_length, fft_overlap)


if __name__ == "__main__":
  main()

