"""
Working UI Integration Example

This script directly saves a pipeline run to the database
to demonstrate the UI functionality.
"""

from uniflow.storage.metadata import SQLiteMetadataStore
from datetime import datetime
import time

print("\n" + "="*70)
print("🌊 UniFlow UI Integration - Direct Database Example")
print("="*70 + "\n")

# Initialize metadata store
store = SQLiteMetadataStore()

# Create a sample run
run_id = f'demo_pipeline_{datetime.now().strftime("%Y%m%d_%H%M%S")}'

print(f"📝 Creating sample pipeline run: {run_id}")

metadata = {
    'run_id': run_id,
    'pipeline_name': 'demo_ml_pipeline',
    'status': 'completed',
    'start_time': datetime.now().isoformat(),
    'end_time': datetime.now().isoformat(),
    'duration': 12.5,
    'success': True,
    'context': {
        'learning_rate': 0.001,
        'epochs': 10,
        'batch_size': 32,
        'model_type': 'neural_network'
    },
    'steps': {
        'load_data': {
            'success': True,
            'duration': 2.3,
            'cached': False,
            'retries': 0,
            'error': None
        },
        'preprocess': {
            'success': True,
            'duration': 1.8,
            'cached': False,
            'retries': 0,
            'error': None
        },
        'train_model': {
            'success': True,
            'duration': 8.1,
            'cached': False,
            'retries': 0,
            'error': None
        },
        'evaluate': {
            'success': True,
            'duration': 0.3,
            'cached': False,
            'retries': 0,
            'error': None
        }
    }
}

print("💾 Saving to metadata database...")
store.save_run(run_id, metadata)

print(f"✅ Run saved successfully!")
print(f"\n🌐 **View in UI:**")
print(f"   Dashboard: http://localhost:8080")
print(f"   All Runs: http://localhost:8080/runs")
print(f"   This Run: http://localhost:8080/runs/{run_id}")

print(f"\n💡 **Refresh your browser to see the run!**")
print(f"   You should see 'demo_ml_pipeline' in the dashboard")

print("\n" + "="*70)
print("✨ The UI integration is working! The pipeline framework will")
print("   automatically save runs once the module reload issue is fixed.")
print("="*70 + "\n")
