import sys
import os
import argparse
import numpy as np
from PIL import Image
# CAFFE_ROOT = '/home/roix/miniconda3/envs/intelcaffe'
import caffe
import inference_output as io
import logging as log


def build_argparser():
    parser = argparse.ArgumentParser()
    parser.add_argument('-m', '--model', help = 'Path to an .caffemodel \
        file with a trained weights.', required = True, type = str, dest = 'model_caffemodel')
    parser.add_argument('-w', '--weights', help = 'Path to an .prototxt file \
        with a trained model.', required = True, type = str, dest = 'model_prototxt')
    parser.add_argument('-i', '--input', help = 'Path to data', required = True, type = str, 
        dest = 'input')
    parser.add_argument('-b', '--batch_size', help = 'Size of the  \
        processed pack', default = 1, type = int, dest = 'batch_size')
    parser.add_argument('-l', '--labels', help = 'Labels mapping file',
        default = None, type = str, dest = 'labels')
    parser.add_argument('-nt', '--number_top', help = 'Number of top results',
        default = 10, type = int, dest = 'number_top')
    parser.add_argument('-t', '--task', help = 'Output processing method: \
        1.classification 2.detection 3.segmentation. \
        Default: without postprocess',
        default = 'feedforward', type = str, dest = 'task')
    parser.add_argument('--color_map', help = 'Classes color map',
        type = str, default = None, dest = 'color_map')
    parser.add_argument('--prob_threshold', help = 'Probability threshold \
        for detections filtering', default = 0.5, type = float, dest = 'threshold')
    #parser.add_argument('-mi', '--mininfer', help = 'Min inference time of single pass',
    #    type = float, default = 0.0, dest = 'mininfer')
    parser.add_argument('--raw_output', help = 'Raw output without logs',
        default = False, type = bool, dest = 'raw_output')
    return parser


def input_reshape(net, batch_size):
    channels = net.blobs['data'].data.shape[1]
    height = net.blobs['data'].data.shape[2]
    width = net.blobs['data'].data.shape[3]
    net.blobs['data'].reshape(batch_size, channels, height, width)
    net.reshape()

    return net


def load_network(caffemodel, prototxt, batch_size):
    caffe.set_mode_cpu()
    # загружаем сеть
    net = caffe.Net(prototxt, caffemodel, caffe.TEST)
    # Меняем параметры местами, чтобы корректно обработать пришедшую картинку
    transformer = caffe.io.Transformer({'data': net.blobs['data'].data.shape})
    transformer.set_transpose('data', (2,0,1))
    transformer.set_channel_swap('data', (2,1,0))
    transformer.set_raw_scale('data', 255.0)

    if batch_size > 1:
        net = input_reshape(net, batch_size)

    return net, transformer


def create_list_images(input):
    images = []
    input_is_correct = True
    if os.path.exists(input):
        if os.path.isdir(input):
            path = os.path.abspath(input)
            # path = os.path(input[0])
            images = [os.path.join(path, file) for file in os.listdir(path)]
        elif os.path.isfile(input):
            for image in input:
                if not os.path.isfile(image):
                    input_is_correct = False
                    break
                images.append(os.path.abspath(image))
        else:
            input_is_correct = False
    if not input_is_correct:
        raise ValueError("Wrong path to image or to directory with images")

    return images


def load_images_to_network(input, net, transformer):
    image_paths = create_list_images(input)
    for i in range(len(image_paths)):
        im = np.array(Image.open(image_paths[i]))
        net.blobs['data'].data[i,:,:,:] = transformer.preprocess('data', im)


def main():
    log.basicConfig(format = '[ %(levelname)s ] %(message)s',
        level = log.INFO, stream = sys.stdout)
    args = build_argparser().parse_args()
    
    try:
        net, transformer = load_network(args.model_caffemodel, 
            args.model_prototxt, args.batch_size)

        load_images_to_network(args.input, net, transformer)
        input = create_list_images(args.input)

        # Прямой проход по сети
        result = net.forward()
    
        # Вывод
        if not args.raw_output:
            io.infer_output(net, result, input, args.labels, args.number_top,
                args.threshold, args.color_map, log, args.task)
        #    result_output(average_time, fps, latency, log)
        # else:
        #    raw_result_output(average_time, fps, latency)
        
        # todo:
        # fps, latency
    except Exception as ex:
        print('ERROR! : {0}'.format(str(ex)))
        sys.exit(1)
    

if __name__ == '__main__':
   sys.exit(main() or 0)

