from __future__ import print_function
import tensorflow as tf
import numpy as np
import os, sys, cv2
import glob
import shutil
sys.path.append(os.getcwd())
from ..lib.networks.factory import get_network
from ..lib.fast_rcnn.config import cfg, cfg_from_file
from ..lib.fast_rcnn.test import test_ctpn
from ..lib.utils.timer import Timer
from ..lib.text_connector.detectors import TextDetector
from ..lib.text_connector.text_connect_cfg import Config as TextLineCfg

root = "/home/deeple/project/ctpn/text-detection-ctpn/"

def resize_im(im, scale, max_scale=None):
    f = float(scale)/min(im.shape[0], im.shape[1])
    if max_scale != None and f*max(im.shape[0], im.shape[1])>max_scale:
        f=float(max_scale)/max(im.shape[0], im.shape[1])
    return cv2.resize(im, None, None, fx=f, fy=f,interpolation=cv2.INTER_LINEAR), f


def draw_boxes(img, image_name, boxes, scale):
    base_name = image_name.split('/')[-1]
    label = image_name.split('/')[-2]
    anno_dir = os.path.join(root, 'data/results/predictions/')
    if not os.path.exists(anno_dir):
        os.makedirs(anno_dir)
    with open(anno_dir + '/{}.txt'.format(base_name.split('.')[0]), 'w') as f:
        for box in boxes:
            if np.linalg.norm(box[0] - box[1]) < 5 or np.linalg.norm(box[3] - box[0]) < 5:
                continue
            if box[8] >= 0.9:
                color = (0, 255, 0)
            elif box[8] >= 0.8:
                color = (255, 0, 0)
            cv2.line(img, (int(box[0]), int(box[1])), (int(box[2]), int(box[3])), color, 2)
            cv2.line(img, (int(box[0]), int(box[1])), (int(box[4]), int(box[5])), color, 2)
            cv2.line(img, (int(box[6]), int(box[7])), (int(box[2]), int(box[3])), color, 2)
            cv2.line(img, (int(box[4]), int(box[5])), (int(box[6]), int(box[7])), color, 2)

            min_x = min(int(box[0]/scale),int(box[2]/scale),int(box[4]/scale),int(box[6]/scale))
            min_y = min(int(box[1]/scale),int(box[3]/scale),int(box[5]/scale),int(box[7]/scale))
            max_x = max(int(box[0]/scale),int(box[2]/scale),int(box[4]/scale),int(box[6]/scale))
            max_y = max(int(box[1]/scale),int(box[3]/scale),int(box[5]/scale),int(box[7]/scale))

            line = ','.join([str(min_x),str(min_y),str(max_x),str(max_y)])+'\r\n'
            f.write(line)

    img = cv2.resize(img, None, None, fx=1.0/scale, fy=1.0/scale, interpolation=cv2.INTER_LINEAR)

    save_dir = os.path.join(root, 'data/results/labeled/', label)
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    cv2.imwrite(os.path.join(save_dir, base_name), img)

def ctpn(sess, net, image_name):
    timer = Timer()
    timer.tic()

    img = cv2.imread(image_name)
    img, scale = resize_im(img, scale=TextLineCfg.SCALE, max_scale=TextLineCfg.MAX_SCALE)
    scores, boxes = test_ctpn(sess, net, img)

    textdetector = TextDetector()
    boxes = textdetector.detect(boxes, scores[:, np.newaxis], img.shape[:2])
    draw_boxes(img, image_name, boxes, scale)
    timer.toc()
    print(('Detection took {:.3f}s for '
           '{:d} object proposals').format(timer.total_time, boxes.shape[0]))


if __name__ == '__main__':
    if os.path.exists(root + "data/results/"):
        shutil.rmtree(root + "data/results/")
    os.makedirs(root + "data/results/")

    cfg_from_file(root + 'ctpn/text.yml')
    with tf.device('/gpu:0'):
        # init session
        config = tf.ConfigProto(allow_soft_placement=True)
        sess = tf.Session(config=config)
        # load network
        net = get_network("Mobilenet_test")
        # load model
        print(('Loading network {:s}... '.format("Mobilenet_test")), end=' ')
        saver = tf.train.Saver()

        try:
            ckpt = tf.train.get_checkpoint_state(cfg.TEST.checkpoints_path)
            print('Restoring from {}...'.format(ckpt.model_checkpoint_path), end=' ')
            saver.restore(sess, ckpt.model_checkpoint_path)
            print('done')
        except:
            raise 'Check your pretrained {:s}'.format(ckpt.model_checkpoint_path)

        im = 128 * np.ones((300, 300, 3), dtype=np.uint8)
        for i in range(2):
            _, _ = test_ctpn(sess, net, im)

        stick_dir = os.path.join(root, 'data/0730/samples0730_resize')
        img_list = []
        for _sub in os.listdir(stick_dir):
            sub_dir = os.path.join(stick_dir, _sub)
            for img_name in os.listdir(sub_dir):
                img_list.append(os.path.join(sub_dir, img_name))
            # im_names = glob.glob(os.path.join(stick_dir, _sub, '*.png')) + \
            #            glob.glob(os.path.join(stick_dir, _sub, '*.jpg'))

        for im_name in img_list:
            print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
            print(('Demo for {:s}'.format(im_name)))
            ctpn(sess, net, im_name)



