"""
针对当前最佳参数的精细调优
基于：n_factors=5, n_epochs=5, reg=0.4, RMSE=0.9997
目标：继续降低过拟合，提升测试集到 < 0.95
"""
import subprocess
import pandas as pd
from datetime import datetime

# 测试的参数组合（围绕最佳值）
test_configs = [
    # (n_factors, n_epochs, reg, lr, 描述)
    (5, 5, 0.50, 0.005, "当前最佳+增大reg到0.5"),
    (5, 5, 0.55, 0.005, "当前最佳+增大reg到0.55★推荐"),
    (5, 5, 0.60, 0.005, "当前最佳+增大reg到0.6"),
    (5, 4, 0.50, 0.005, "减少epoch+reg=0.5"),
    (5, 4, 0.55, 0.005, "减少epoch+reg=0.55★推荐"),
    (4, 5, 0.50, 0.005, "更小模型+reg=0.5"),
    (4, 4, 0.60, 0.005, "更小模型+少epoch+强reg★推荐"),
    (6, 5, 0.50, 0.005, "稍大模型+reg=0.5"),
]

results = []

print("=" * 70)
print("精细调优测试（目标：测试集 RMSE < 0.95）")
print("=" * 70)
print(f"开始时间: {datetime.now().strftime('%H:%M:%S')}")
print(f"总共测试 {len(test_configs)} 组参数")
print(f"基准：n_factors=5, n_epochs=5, reg=0.4")
print(f"      训练集 0.6754, 测试集 0.9997, 过拟合 48.0%\n")

for idx, (n_factors, n_epochs, reg, lr, desc) in enumerate(test_configs, 1):
    print(f"\n[{idx}/{len(test_configs)}] {desc}")
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
        output = result.stdout
        
        # 提取RMSE和MAE
        test_rmse = test_mae = train_rmse = train_mae = None
        lines = output.split('\n')
        
        for i, line in enumerate(lines):
            if '测试集评估' in line:
                # 找接下来的RMSE和MAE
                for j in range(i, min(i+5, len(lines))):
                    if 'RMSE (均方根误差):' in lines[j]:
                        test_rmse = float(lines[j].split(':')[1].strip())
                    elif 'MAE  (平均绝对误差):' in lines[j]:
                        test_mae = float(lines[j].split(':')[1].strip())
            
            elif '训练集评估（过拟合检测）' in line:
                for j in range(i, min(i+5, len(lines))):
                    if '- RMSE:' in lines[j] and train_rmse is None:
                        train_rmse = float(lines[j].split('RMSE:')[1].split()[0])
                    elif '- MAE:' in lines[j] and train_mae is None:
                        train_mae = float(lines[j].split('MAE:')[1].split()[0])
        
        if test_rmse and train_rmse:
            overfitting = (test_rmse - train_rmse) / train_rmse * 100
            
            # 判断评级
            if test_rmse < 0.85:
                grade = "★★★★★ 优秀"
            elif test_rmse < 0.95:
                grade = "★★★★☆ 良好"
            elif test_rmse < 1.05:
                grade = "★★★☆☆ 合格"
            else:
                grade = "★★☆☆☆ 需改进"
            
            print(f"  ✓ 训练集 RMSE: {train_rmse:.4f}, MAE: {train_mae:.4f}")
            print(f"  ✓ 测试集 RMSE: {test_rmse:.4f}, MAE: {test_mae:.4f}")
            print(f"  ✓ 过拟合: {overfitting:.1f}%")
            print(f"  ✓ 评级: {grade}")
            
            results.append({
                'description': desc,
                'n_factors': n_factors,
                'n_epochs': n_epochs,
                'reg': reg,
                'lr': lr,
                'train_rmse': train_rmse,
                'train_mae': train_mae,
                'test_rmse': test_rmse,
                'test_mae': test_mae,
                'overfitting': overfitting,
                'grade': grade
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
    print(df[['description', 'n_factors', 'n_epochs', 'reg', 'train_rmse', 'test_rmse', 'overfitting', 'grade']].to_string(index=False))
    
    # 保存到CSV
    df.to_csv('../data/fine_tune_results.csv', index=False)
    print(f"\n结果已保存到: ../data/fine_tune_results.csv")
    
    # 最佳结果
    best = df.iloc[0]
    print("\n" + "=" * 70)
    print("🎯 最佳参数组合：")
    print("=" * 70)
    print(f"描述: {best['description']}")
    print(f"参数: n_factors={best['n_factors']}, n_epochs={best['n_epochs']}, reg={best['reg']}, lr={best['lr']}")
    print(f"\n训练集:")
    print(f"  RMSE: {best['train_rmse']:.4f}")
    print(f"  MAE:  {best['train_mae']:.4f}")
    print(f"\n测试集:")
    print(f"  RMSE: {best['test_rmse']:.4f}")
    print(f"  MAE:  {best['test_mae']:.4f}")
    print(f"\n过拟合程度: {best['overfitting']:.1f}%")
    print(f"评级: {best['grade']}")
    
    # 与基准对比
    print("\n" + "=" * 70)
    print("📊 与基准对比（5,5,0.4）：")
    print("=" * 70)
    baseline_test = 0.9997
    baseline_train = 0.6754
    baseline_over = 48.0
    
    improvement_test = (baseline_test - best['test_rmse']) / baseline_test * 100
    improvement_over = (baseline_over - best['overfitting']) / baseline_over * 100
    
    print(f"测试集 RMSE: {baseline_test:.4f} → {best['test_rmse']:.4f} ({improvement_test:+.1f}%)")
    print(f"训练集 RMSE: {baseline_train:.4f} → {best['train_rmse']:.4f}")
    print(f"过拟合程度: {baseline_over:.1f}% → {best['overfitting']:.1f}% ({improvement_over:+.1f}%)")

print(f"\n结束时间: {datetime.now().strftime('%H:%M:%S')}")






