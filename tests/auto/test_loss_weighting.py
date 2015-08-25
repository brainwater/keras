from __future__ import absolute_import
from __future__ import print_function

import numpy as np
np.random.seed(1336)  # for reproducibility

from keras.datasets import mnist
from keras.models import Sequential, Graph
from keras.layers.core import Dense, Activation, RepeatVector, TimeDistributedDense
from keras.layers.recurrent import SimpleRNN
from keras.utils import np_utils
import unittest

nb_classes = 10
batch_size = 128
nb_epoch = 8
weighted_class = 9
standard_weight = 1
high_weight = 5
max_train_samples = 5000
max_test_samples = 1000

# the data, shuffled and split between tran and test sets
(X_train, y_train), (X_test, y_test) = mnist.load_data()
X_train = X_train.reshape(60000, 784)[:max_train_samples]
X_test = X_test.reshape(10000, 784)[:max_test_samples]
X_train = X_train.astype("float32") / 255
X_test = X_test.astype("float32") / 255

# convert class vectors to binary class matrices
y_train = y_train[:max_train_samples]
y_test = y_test[:max_test_samples]
Y_train = np_utils.to_categorical(y_train, nb_classes)
Y_test = np_utils.to_categorical(y_test, nb_classes)
test_ids = np.where(y_test == np.array(weighted_class))[0]

class_weight = dict([(i, standard_weight) for i in range(nb_classes)])
class_weight[weighted_class] = high_weight

sample_weight = np.ones((y_train.shape[0])) * standard_weight
sample_weight[y_train == weighted_class] = high_weight


def create_sequential_model():
    model = Sequential()
    model.add(Dense(784, 50))
    model.add(Activation('relu'))
    model.add(Dense(50, 10))
    model.add(Activation('softmax'))
    return model


def create_graph_model():
    model = Graph()
    model.add_input(name='input')
    model.add_node(Dense(784, 50, activation='relu'), name='d1', input='input')
    model.add_node(Dense(50, 10, activation='softmax'), name='d2', input='d1')
    model.add_output(name='output', input='d2')
    return model

def create_sequential_seq_model():
    model = Sequential()
    model.add(SimpleRNN(2, 2, init='one', return_sequences=True))
    return model

def create_graph_seq_model():
    model = Graph()
    model.add_input(name='input', ndim=3)
    model.add_node(SimpleRNN(2, 2, init='one', return_sequences=True), name='rnn', input='input')
    model.add_output(name='output', input='rnn')
    return model


def _test_weights_sequential(model, class_weight=None, sample_weight=None):
    if sample_weight is not None:
        model.fit(X_train, Y_train, batch_size=batch_size, nb_epoch=nb_epoch // 3, verbose=0,
                  class_weight=class_weight, sample_weight=sample_weight)
        model.fit(X_train, Y_train, batch_size=batch_size, nb_epoch=nb_epoch // 3, verbose=0,
                  class_weight=class_weight, sample_weight=sample_weight, validation_split=0.1)
        model.fit(X_train, Y_train, batch_size=batch_size, nb_epoch=nb_epoch // 3, verbose=0,
                  class_weight=class_weight, sample_weight=sample_weight, validation_data=(X_train, Y_train, sample_weight))
    else:
        model.fit(X_train, Y_train, batch_size=batch_size, nb_epoch=nb_epoch // 2, verbose=0,
                  class_weight=class_weight, sample_weight=sample_weight)
        model.fit(X_train, Y_train, batch_size=batch_size, nb_epoch=nb_epoch // 2, verbose=0,
                  class_weight=class_weight, sample_weight=sample_weight, validation_split=0.1)

    model.train_on_batch(X_train[:32], Y_train[:32],
                         class_weight=class_weight, sample_weight=sample_weight[:32] if sample_weight is not None else None)
    model.test_on_batch(X_train[:32], Y_train[:32],
                        sample_weight=sample_weight[:32] if sample_weight is not None else None)
    score = model.evaluate(X_test[test_ids, :], Y_test[test_ids, :], verbose=0)
    return score


def _test_weights_graph(model, class_weight=None, sample_weight=None):
    model.fit({'input': X_train, 'output': Y_train}, batch_size=batch_size, nb_epoch=nb_epoch // 2, verbose=0,
              class_weight={'output': class_weight}, sample_weight={'output': sample_weight})
    model.fit({'input': X_train, 'output': Y_train}, batch_size=batch_size, nb_epoch=nb_epoch // 2, verbose=0,
              class_weight={'output': class_weight}, sample_weight={'output': sample_weight}, validation_split=0.1)

    model.train_on_batch({'input': X_train[:32], 'output': Y_train[:32]},
                         class_weight={'output': class_weight}, sample_weight={'output': sample_weight[:32] if sample_weight is not None else None})
    model.test_on_batch({'input': X_train[:32], 'output': Y_train[:32]},
                        sample_weight={'output': sample_weight[:32] if sample_weight is not None else None})
    score = model.evaluate({'input': X_test[test_ids, :], 'output': Y_test[test_ids, :]}, verbose=0)
    return score


class TestLossWeighting(unittest.TestCase):
    def test_sequential(self):
        for loss in ['mae', 'mse', 'categorical_crossentropy']:
            print('loss:', loss)
            print('sequential')
            # no weights: reference point
            model = create_sequential_model()
            model.compile(loss='categorical_crossentropy', optimizer='rmsprop')
            standard_score = _test_weights_sequential(model)
            # test class_weight
            model = create_sequential_model()
            model.compile(loss=loss, optimizer='rmsprop')
            score = _test_weights_sequential(model, class_weight=class_weight)
            print('score:', score, ' vs.', standard_score)
            self.assertTrue(score < standard_score)
            # test sample_weight
            model = create_sequential_model()
            model.compile(loss=loss, optimizer='rmsprop')
            score = _test_weights_sequential(model, sample_weight=sample_weight)
            print('score:', score, ' vs.', standard_score)
            self.assertTrue(score < standard_score)
            
    def test_sequential_seq(self):
        print("Testing sample weights on a sequential model with sequential output")
        model = create_sequential_seq_model()
        model.compile(loss='mse', optimizer='rmsprop')
        #X = np.array([np.array([1.])])
        X = np.array(
            [[[1, 1], [2, 1], [3, 1], [5, 5]],
             [[1, 5], [5, 0], [0, 0], [0, 0]]], dtype=np.int32)
        ys = model.predict(X)
        mask = [[1.,1.,1.,1.],
                [1.,1.,0.,0.]]
        model.fit(X, ys, nb_epoch=1, batch_size=2, verbose=1, sample_weight=mask)
        #loss = model.fit(X, ys, nb_epoch=1, batch_size=2, verbose=1).history['loss'][0]
        
    def test_graph_seq(self):
        print("Testing sample weights on a graph with sequential output")
        model = create_graph_seq_model()
        model.compile(loss={'output': 'mse'}, optimizer='rmsprop')
        X = np.array(
            [[[1, 1], [2, 1], [3, 1], [5, 5]],
             [[1, 5], [5, 0], [0, 0], [0, 0]]], dtype=np.int32)
        ins = { 'input': X, }
        ys = model.predict(ins)
        masks = {
            'output': [[1.,1.,1.,1.],
                       [1.,1.,0.,0.]],
        }
        data = { 'input': X,
                 'output': ys['output'] }
        #model.fit(data, nb_epoch=1, batch_size=2, verbose=1)
        model.fit(data, nb_epoch=1, batch_size=2, verbose=1, sample_weight=masks)

    def test_graph(self):
        for loss in ['mae', 'mse', 'categorical_crossentropy']:
            print('loss:', loss)
            print('graph')
            # no weights: reference point
            model = create_graph_model()
            model.compile(loss={'output': 'categorical_crossentropy'}, optimizer='rmsprop')
            standard_score = _test_weights_graph(model)
            # test class_weight
            model = create_graph_model()
            model.compile(loss={'output': 'categorical_crossentropy'}, optimizer='rmsprop')
            score = _test_weights_graph(model, class_weight=class_weight)
            print('score:', score, ' vs.', standard_score)
            self.assertTrue(score < standard_score)
            # test sample_weight
            model = create_graph_model()
            model.compile(loss={'output': 'categorical_crossentropy'}, optimizer='rmsprop')
            score = _test_weights_graph(model, sample_weight=sample_weight)
            print('score:', score, ' vs.', standard_score)
            self.assertTrue(score < standard_score)


if __name__ == '__main__':
    print('Test class_weight and sample_weight')
    unittest.main()
