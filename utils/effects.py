from pysndfx import AudioEffectsChain


def do_reverb_transform(sound,
                        reverberance=100,
                        hf_damping=50,
                        room_scale=50,
                        stereo_depth=100,
                        pre_delay=20,
                        wet_gain=0,
                        wet_only=False):
  transformer = (
    AudioEffectsChain().
    reverb(reverberance=reverberance,
           hf_damping=hf_damping,
           room_scale=room_scale,
           stereo_depth=stereo_depth,
           pre_delay=pre_delay,
           wet_gain=wet_gain,
           wet_only=wet_only)
  )

  return transformer(sound)