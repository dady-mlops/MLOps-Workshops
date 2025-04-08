#!/usr/bin/env python
# -*- coding: utf-8 -*-

import torch
import json

def check_gpu():
    """Check if GPU is available and return basic info"""
    result = {
        "cuda_available": torch.cuda.is_available(),
        "device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0
    }
    
    # Add device name if GPU available
    if result["cuda_available"] and result["device_count"] > 0:
        try:
            result["device_name"] = torch.cuda.get_device_name(0)
        except:
            result["device_name"] = "Unknown GPU"
            
    return result

if __name__ == "__main__":
    result = check_gpu()
    print(json.dumps(result, indent=2))
    
    # Write result to file for other scripts
    with open("gpu_check_result.json", "w") as f:
        json.dump(result, f, indent=2)
    
    # Exit with success code if GPU available
    exit(0 if result["cuda_available"] else 1) 