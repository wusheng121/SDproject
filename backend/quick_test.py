"""
快速测试多组参数
基于你已找到的最佳参数附近搜索
"""
import subprocess
import pandas as pd
from datetime import datetime

# 测试的参数组合
test_configs = [
    # (n_factors, n_epochs, reg, lr, 描述)
    (7, 12, 0.35, 0.005, "基准+更大reg"),
    (7, 12, 0.40, 0.005, "基准+强reg"),
    (6, 10, 0.35, 0.005, "更小模型+大reg"),
    (6, 10, 0.40, 0.005, "更小模型+强reg"),
    (5, 10, 0.40, 0.005, "最小模型+强reg"),
    (7, 10, 0.35, 0.005, "减少轮数+大reg"),
    (7, 8,  0.40, 0.005, "减少轮数+强reg"),
]

results = []

print("=" * 70)
print("快速参数测试")
print("=" * 70)
print(f"开始时间: {datetime.now().strftime('%H:%M:%S')}")
print(f"总共测试 {len(test_configs)} 组参数\n")

for idx, (n_factors, n_epochs, reg, lr, desc) in enumerate(test_configs, 1):
    print(f"\n[{idx}/{len(test_configs)}] 测试: {desc}")
    print(f"  参数: n_factors={n_factors}, n_epochs={n_epochs}, reg={reg}, lr={lr}")
    
    cmd = [
        "python", "-m", "ml.train_mf",
        "--train", "../data/output1/ratings_train.csv",
        "--test", "../data/output1/ratings_test.csv",
        "--output", "../data/output2_test/",
        "--n-factors", str(n_factors),
        "--n-epochs", str(n_epochs),
        "--reg", str(reg),
        "--lr", str(lr)
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        
        # 简单解析输出（从控制台输出中提取RMSE）
        output = result.stdout
        
        # 提取测试集和训练集RMSE
        test_rmse = train_rmse = None
        for line in output.split('\n'):
            if 'RMSE (均方根误差):' in line:
                test_rmse = float(line.split(':')[1].strip())
            elif '训练集评估' in output and 'RMSE:' in line and train_rmse is None:
                parts = line.split('RMSE:')
                if len(parts) > 1:
                    train_rmse = float(parts[1].split()[0])
        
        if test_rmse and train_rmse:
            overfitting = (test_rmse - train_rmse) / train_rmse * 100
            print(f"  ✓ 训练集 RMSE: {train_rmse:.4f}")
            print(f"  ✓ 测试集 RMSE: {test_rmse:.4f}")
            print(f"  ✓ 过拟合: {overfitting:.1f}%")
            
            results.append({
                'description': desc,
                'n_factors': n_factors,
                'n_epochs': n_epochs,
                'reg': reg,
                'lr': lr,
                'train_rmse': train_rmse,
                'test_rmse': test_rmse,
                'overfitting': overfitting
            })
        else:
            print(f"  ✗ 解析失败")
            
    except Exception as e:
        print(f"  ✗ 错误: {e}")

# 保存结果
if results:
    df = pd.DataFrame(results)
    df = df.sort_values('test_rmse')
    
    print("\n" + "=" * 70)
    print("测试完成！结果汇总（按测试集RMSE排序）")
    print("=" * 70)
    print(df.to_string(index=False))
    
    # 保存到CSV
    df.to_csv('../data/quick_test_results.csv', index=False)
    print(f"\n结果已保存到: ../data/quick_test_results.csv")
    
    best = df.iloc[0]
    print("\n" + "=" * 70)
    print("最佳参数组合：")
    print("=" * 70)
    print(f"描述: {best['description']}")
    print(f"n_factors={best['n_factors']}, n_epochs={best['n_epochs']}, reg={best['reg']}, lr={best['lr']}")
    print(f"训练集 RMSE: {best['train_rmse']:.4f}")
    print(f"测试集 RMSE: {best['test_rmse']:.4f}")
    print(f"过拟合程度: {best['overfitting']:.1f}%")

print(f"\n结束时间: {datetime.now().strftime('%H:%M:%S')}")





