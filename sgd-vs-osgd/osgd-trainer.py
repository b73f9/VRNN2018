# -*- coding: utf-8 -*-
"""Untitled0.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1ty9A2XHWSclZ-z6fqHeAvVBFYj1EyTMT
"""

#======================================================================
#======================================================================
#                  CIFAR 10
#======================================================================
#======================================================================

from __future__ import print_function
import keras
from keras.datasets import mnist
from keras.models import Sequential
from keras.layers import Dense, Dropout, Activation, Flatten
from keras.layers import Conv2D, MaxPooling2D
from keras import backend as K
import tensorflow
import numpy as np
from keras import datasets
from keras.optimizers import Optimizer
from keras.utils.generic_utils import serialize_keras_object
from keras.utils.generic_utils import deserialize_keras_object
from keras.legacy import interfaces
import logging
import time

logging.basicConfig(level=logging.DEBUG)

num_classes = 10

def load_cifar10_data():
    cifar10 = datasets.cifar10
    (x_train_cifar, y_train_cifar),(x_test_cifar, y_test_cifar) = cifar10.load_data()
    x_train_cifar = x_train_cifar.astype('float32') / 255.0
    x_test_cifar = x_test_cifar.astype('float32') / 255.0

    return (x_train_cifar, y_train_cifar), (x_test_cifar, y_test_cifar)

input_shape_cifar = (32, 32, 3)
train_cifar, test_cifar = load_cifar10_data()
x_train_cifar = train_cifar[0]
x_test_cifar = test_cifar[0]

y_train_cifar = keras.utils.to_categorical(train_cifar[1], num_classes)
y_test_cifar = keras.utils.to_categorical(test_cifar[1], num_classes)



def buildCifar():
    model = Sequential()
    model.add(Conv2D(32, (3, 3), padding='same',
                     input_shape=x_train_cifar.shape[1:]))
    model.add(Activation('relu'))
    model.add(Conv2D(32, (3, 3)))
    model.add(Activation('relu'))
    model.add(MaxPooling2D(pool_size=(2, 2)))
    model.add(Dropout(0.25))

    model.add(Conv2D(64, (3, 3), padding='same'))
    model.add(Activation('relu'))
    model.add(Conv2D(64, (3, 3)))
    model.add(Activation('relu'))
    model.add(MaxPooling2D(pool_size=(2, 2)))
    model.add(Dropout(0.25))

    model.add(Flatten())
    model.add(Dense(512))
    model.add(Activation('relu'))
    model.add(Dropout(0.5))
    model.add(Dense(num_classes))
    model.add(Activation('softmax'))

    model.compile(loss=keras.losses.categorical_crossentropy,
                optimizer=keras.optimizers.SGD(),
                metrics=['accuracy'])
    
    return model



class RAISTrainer():
    def __init__(self, model):
        self.model = model
        self.logger = logging.getLogger("RAISTrainer")
    
        layer=-1
        grads = model.optimizer.get_gradients(model.total_loss, model.layers[layer].output)
        symb_inputs = (model._feed_inputs + model._feed_targets + model._feed_sample_weights)
        self.f_grads = K.function(symb_inputs, grads)
    
    def _get_grads(self, xs, ys):
        x, y, sample_weight = self.model._standardize_user_data(xs, ys)
        output_grad = self.f_grads(x + y + sample_weight)
        return output_grad

    def _get_distribution(self, xs, ys):
        #self.logger.info("Updating distribution...")
        n = xs.shape[0]
        k = 1000
        p = np.zeros(xs.shape[0])
        for i in range((n-1) // k + 1):
            fst = i*k
            snd = min(n, (i+1) * k)
            grads = self._get_grads(xs[fst:snd], ys[fst:snd])[0]
            v = np.linalg.norm(grads, axis=1)
            p[fst:snd] = v    
        return p / p.sum()

    def _test_on_validation(self, validation_data):
        valid_x, valid_y = validation_data
        loss, acc = self.model.test_on_batch(valid_x, valid_y)
        self.logger.info("========== Validation loss: " + str(loss) + " acc: " + str(acc))
        return [(loss, acc)]
      
    def train(self, train_x, train_y, batch_size=16, epochs=1, validation_data=None, update_distributions=False):
        N = train_x.shape[0]
        steps_per_epoch = N // batch_size
        
        time_epochs = []
        res = []

        for e_n in range(1, epochs+1):
          
          time_start = time.time()
          
          self.logger.info("==== Epoch " + str(e_n) + " started")
          for b_n in range(1, steps_per_epoch+1):
            if update_distributions:
              p = self._get_distribution(train_x, train_y)
              indicies = np.random.choice(N, batch_size, p=p)
            else:
              indicies = np.random.choice(N, batch_size)
            batch_x = np.take(train_x, indicies, axis=0)
            batch_y = np.take(train_y, indicies, axis=0)
            loss, acc = self.model.train_on_batch(batch_x, batch_y)
            #res += [(loss, acc)]
            if b_n % 10 == 0:
              self.logger.info(str(b_n) + "/" + str(steps_per_epoch) + " loss: " + str(loss) + " acc: " + str(acc))
              if validation_data is not None:
                res += self._test_on_validation(validation_data)
              
          time_epochs += [time.time() - time_start]
          
          self.logger.info(str(b_n) + "/" + str(steps_per_epoch) + " loss: " + str(loss) + " acc: " + str(acc))
         
          if validation_data is not None:
            res += self._test_on_validation(validation_data)
        return res, time_epochs

N=10
E=10
BS=256

SGD_RES = []
for idx in range(N):
    sgd = RAISTrainer(buildCifar())
    r = sgd.train(x_train_cifar, y_train_cifar,
                          validation_data=(x_test_cifar, y_test_cifar),
                          epochs=E, batch_size=256)
    SGD_RES += [r]

OSGD_RES = []
for idx in range(N):
    osgd = RAISTrainer(buildCifar())
    r = osgd.train(x_train_cifar, y_train_cifar,
                          validation_data=(x_test_cifar, y_test_cifar),
                          update_distributions=True, 
                          epochs=E, batch_size=256)
    OSGD_RES += [r]


def to_np(res):
  n = len(res)
  accs = []
  losses = []
  times = []
  for r in res:
    alist = [x for _, x in r[0]]
    llist = [x for x, _ in r[0]]
    tlist = r[1]
    times.append(tlist)
    accs.append(alist)
    losses.append(llist)
  return np.array(accs), np.array(losses), np.array(times)

sgd_arrs = to_np(SGD_RES)

osgd_arrs = to_np(OSGD_RES)



np.save('sgd_accs_x%de10' % N, sgd_arrs[0])
np.save('osgd_accs_x%de10'% N, osgd_arrs[0])

np.save('sgd_loss_x%de10'% N, sgd_arrs[1])
np.save('osgd_loss_x%de10'% N, osgd_arrs[1])

np.save('sgd_times_x%de10'% N, sgd_arrs[2])
np.save('osgd_times_x%de10'% N, osgd_arrs[2])
