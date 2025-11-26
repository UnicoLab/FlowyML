"""
Tests for pipeline templates.
"""

import unittest
from uniflow.core.templates import (
    create_from_template,
    list_templates,
    MLTrainingTemplate,
    DataPipelineTemplate,
    ABTestPipelineTemplate,
    TEMPLATES
)
from uniflow.core.pipeline import Pipeline

class TestPipelineTemplates(unittest.TestCase):
    
    def test_list_templates(self):
        """Test listing available templates."""
        templates = list_templates()
        
        self.assertIn('ml_training', templates)
        self.assertIn('etl', templates)
        self.assertIn('data_pipeline', templates)
        self.assertIn('ab_test', templates)
        
    def test_ml_training_template(self):
        """Test ML training template."""
        def load_data():
            return {"data": "loaded"}
            
        def preprocess(dataset):
            return {"data": "processed"}
            
        def train(processed_data):
            return {"model": "trained"}
            
        pipeline = create_from_template(
            'ml_training',
            name='test_ml',
            data_loader=load_data,
            preprocessor=preprocess,
            trainer=train
        )
        
        self.assertIsInstance(pipeline, Pipeline)
        self.assertEqual(pipeline.name, 'test_ml')
        self.assertEqual(len(pipeline.steps), 3)
        
    def test_etl_template(self):
        """Test ETL template."""
        def extract():
            return {"raw": "data"}
            
        def transform(raw_data):
            return {"transformed": "data"}
            
        def load(transformed_data):
            return True
            
        pipeline = create_from_template(
            'etl',
            name='test_etl',
            extractor=extract,
            transformer=transform,
            loader=load
        )
        
        self.assertIsInstance(pipeline, Pipeline)
        self.assertEqual(len(pipeline.steps), 3)
        
    def test_ab_test_template(self):
        """Test A/B test template."""
        def load_data():
            return {"data": "test"}
            
        def train_a(data):
            return {"model": "a"}, {"accuracy": 0.85}
            
        def train_b(data):
            return {"model": "b"}, {"accuracy": 0.90}
            
        def compare(metrics_a, metrics_b):
            return "b" if metrics_b['accuracy'] > metrics_a['accuracy'] else "a"
            
        pipeline = create_from_template(
            'ab_test',
            name='test_ab',
            data_loader=load_data,
            model_a_trainer=train_a,
            model_b_trainer=train_b,
            comparator=compare
        )
        
        self.assertIsInstance(pipeline, Pipeline)
        self.assertGreaterEqual(len(pipeline.steps), 1)
        
    def test_invalid_template(self):
        """Test error handling for invalid template."""
        with self.assertRaises(ValueError):
            create_from_template('nonexistent_template')
            
    def test_template_with_context(self):
        """Test template with context parameters."""
        def load_data():
            return {}
            
        pipeline = create_from_template(
            'ml_training',
            name='test_with_context',
            data_loader=load_data,
            learning_rate=0.001,
            epochs=10
        )
        
        self.assertIsInstance(pipeline, Pipeline)
        # Context params should be in pipeline.context
        self.assertIsNotNone(pipeline.context)

if __name__ == '__main__':
    unittest.main()
