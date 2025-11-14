#!/usr/bin/env python3
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from flask import Flask, request, jsonify
from flask_cors import CORS
import os, tempfile
from pathlib import Path
import pandas as pd

app = Flask(__name__)
CORS(app)
Path('inputs').mkdir(exist_ok=True)
Path('outputs').mkdir(exist_ok=True)

@app.route('/', methods=['GET'])
def index():
    with open('index.html', encoding='utf-8') as f:
        return f.read(), 200, {'Content-Type': 'text/html; charset=utf-8'}

@app.route('/process', methods=['POST'])
def process():
    try:
        from etl_pipeline import ETLPipeline
        import pandas as pd
        
        content = request.get_data(as_text=True)
        if not content.strip():
            return jsonify({'error': 'No data'}), 400
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', dir='inputs', delete=False, encoding='utf-8') as f:
            f.write(content)
            fname = os.path.basename(f.name)
        
        pipeline = ETLPipeline(input_dir='inputs', output_dir='outputs')
        df, schema = pipeline.run(fname)
        
        # Infer column types before converting to string
        column_types = {}
        for col in df.columns:
            # Check if column contains arrays/lists
            if df[col].apply(lambda x: isinstance(x, (list, tuple))).any():
                column_types[col] = 'array'
            elif pd.api.types.is_numeric_dtype(df[col]):
                column_types[col] = 'number'
            elif pd.api.types.is_bool_dtype(df[col]):
                column_types[col] = 'boolean'
            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                column_types[col] = 'datetime'
            else:
                column_types[col] = 'string'
        
        print(f"DEBUG - Column types detected: {column_types}", flush=True)
        
        # Convert to JSON-safe format while preserving arrays and numeric types
        data = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                val = row[col]
                # Keep arrays as-is for JSON serialization
                if isinstance(val, list):
                    record[col] = val
                # Keep numeric columns as numbers
                elif col in ['total_items']:
                    record[col] = int(val) if pd.notna(val) else 0
                # For NaN values, skip them (don't include in record)
                elif pd.isna(val):
                    continue
                # Convert everything else to string
                else:
                    record[col] = str(val)
            data.append(record)
        
        try:
            os.remove(os.path.join('inputs', fname))
        except:
            pass
        
        print(f"DEBUG - Returning types: {column_types}", flush=True)
        return jsonify({'success': True, 'data': data, 'types': column_types}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("Server starting...", flush=True)
    app.run(host='127.0.0.1', port=5000, debug=False)
