import numpy as np


def interleave(deinterleaved):
    deinterleaved = np.array(deinterleaved)
    channels = deinterleaved.shape[1]
    if channels == 1:
        return deinterleaved.T[0]
    interleaved = np.empty(deinterleaved.size)
    for channel in range(channels):
        interleaved[channel::channels] = deinterleaved[:, channel].T
    return interleaved


def deinterleave(interleaved, channels):
    interleaved = np.array(interleaved)
    if channels == 1:
        return interleaved[None, :].T
    interleaved = np.array(interleaved)
    numberOfFrames = int(interleaved.size / channels)
    deinterleaved = np.empty([numberOfFrames, channels])
    for channel in range(channels):
        deinterleaved[:, channel] = interleaved[channel::channels]
    return deinterleaved


def decode_pcm_samples(samples, bitdepth):
    numberOfSamples = len(samples) // (bitdepth // 8)
    if(bitdepth == 16):
        decodedSamples = np.frombuffer(samples, dtype='int16')
    elif(bitdepth == 24):
        samples_8bit = np.frombuffer(samples, dtype='int8')
        decodedSamples = np.zeros(numberOfSamples, dtype='int32')
        decodedSamples.view(dtype='int8')[0::4] = samples_8bit[0::3]
        decodedSamples.view(dtype='int8')[1::4] = samples_8bit[1::3]
        decodedSamples.view(dtype='int8')[2::4] = samples_8bit[2::3]
        decodedSamples[decodedSamples > 2**23 - 1] = (
            decodedSamples[decodedSamples > 2**23 - 1] - 2**24
        )
    elif(bitdepth == 32):
        decodedSamples = np.frombuffer(samples, dtype='int32')
    else:
        raise RuntimeError('unsupported bitdepth')
    return decodedSamples / float((2**(bitdepth - 1) - 1))


def encode_pcm_samples(samples, bitdepth):
    samples = np.array(samples)
    samples[samples > 1.0] = 1.0
    samples[samples < -1.0] = -1.0
    scaledSamples = samples * (2**(bitdepth - 1) - 1)
    if(bitdepth == 16):
        encodedSamples = scaledSamples.astype('int16').tobytes()
    elif(bitdepth == 24):
        encodedSamples = scaledSamples.astype('int32').tobytes()
        encodedSamples = bytearray(encodedSamples)
        del encodedSamples[3::4]
    elif(bitdepth == 32):
        encodedSamples = scaledSamples.astype('int32').tobytes()
    else:
        raise RuntimeError('unsupported bitdepth')
    return encodedSamples
