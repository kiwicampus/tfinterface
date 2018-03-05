import tensorflow as tf

import os

import sys


class CheckpointPredictor(object):
    """ Inference class to abstract evaluation """
    def __init__(self, input_fn, model_fn, model_dir, params, sess = None):
        self.sess = sess
        self.input_fn = input_fn
        self.model_fn = model_fn
        self.model_dir = model_dir
        self.params = params
        self.features = self.input_fn()

        if isinstance(self.features, tuple) and len(self.features) == 2:
            self.features, _ = self.features

        spec = self.model_fn(self.features, None, tf.estimator.ModeKeys.PREDICT, self.params)

        self.predictions = spec.predictions

    def predict(self, **kargs):
        if self.sess is None:
            self.sess = tf.Session()
            saver = tf.train.Saver()
            path = tf.train.latest_checkpoint(self.model_dir)
            saver.restore(self.sess, path)
        
        feed_dict = {self.features[key]: kargs[key] for key in self.features}

        return self.sess.run(self.predictions, feed_dict = feed_dict)

class UFFGenerator(object):

    def __init__(self, input_fn, model_fn, model_dir, params, sess = None):
        self.sess = sess
        self.input_fn = input_fn
        self.model_fn = model_fn
        self.model_dir = model_dir
        self.params = params

        self.graph = tf.Graph()

        with self.graph.as_default():

            self.features = self.input_fn()

            if isinstance(self.features, tuple) and len(self.features) == 2:
                self.features, _ = self.features

            spec = self.model_fn(self.features, None, tf.estimator.ModeKeys.PREDICT, self.params)

            self.predictions = spec.predictions



    def dump(self, uff_path, model_outputs):

        import uff

        with self.graph.as_default(), tf.Session() as sess:
            saver = tf.train.Saver()
            path = tf.train.latest_checkpoint(self.model_dir)
            saver.restore(sess, path)

            model_graph = sess.graph.as_graph_def()

            model_graph = tf.graph_util.convert_variables_to_constants(sess, model_graph, model_outputs)
            model_graph = tf.graph_util.remove_training_nodes(model_graph)

            for elem in model_graph.node:
                print(elem.name)

            uff_model = uff.from_tensorflow(model_graph, model_outputs)

            assert(uff_model)

            uff_folder = os.path.dirname(uff_path)

            if uff_folder and not os.path.exists(uff_folder):
                os.makedirs(uff_folder)

            # define mode based on python version
            if sys.version_info.major > 2:
                mode = "wb"
            else:
                mode = "w"
            
            with open(uff_path, mode) as f:
                f.write(uff_model)

    

class UFFPredictor(object):
    def __init__(self, uff_path, input_nodes, output_nodes, **kwargs):

        import pycuda.driver as cuda
        import pycuda.autoinit
        import tensorrt as trt
        
        self.engine = trt.lite.Engine(
            framework = "uff", 
            path = uff_path, 
            input_nodes = input_nodes, 
            output_nodes = output_nodes,
            **kwargs
        )
    
    def predict(self, *args):
        return self.engine.infer(*args)


# class UFFPredictor(object):
#     def __init__(self, uff_path):