# Urdu agent test run

Passed: 5/5

## 1. PASS

**Question:** Multan mein 28 November ko gandum bona kaisa rahega?

**Answer:**

ملتان میں 28 نومبر کی بوائی کا دباؤ اسکور 3.46 ہے۔ بہترین دن 1 اکتوبر ہے، جس کا اسکور 0.0 ہے۔ اس تاریخ پر بہترین دن کے مقابلے میں دباؤ 3.5 پوائنٹ زیادہ ہے؛ یہ تاریخ محفوظ مدت سے باہر ہے۔ یہ پچھلے 25 سال کے موسم پر مبنی سیمیولیشن ہے، پیش گوئی نہیں۔

**Tool calls:** `[{'tool': 'get_stress_for_date', 'input': {'district': 'Multan', 'date': '11-28'}, 'output': {'district': 'Multan', 'date': '11-28', 'stress_score': 3.46, 'best_day': '10-01', 'best_day_stress_score': 0.0, 'extra_stress_vs_best': 3.5, 'inside_safest_window': False, 'safest_window': ['10-01', '11-23'], 'data_is_fake': False}}]`

---

## 2. PASS

**Question:** Faislabad mein 15 November ko bijai karun to kya hoga?

**Answer:**

فیصل آباد میں 15 نومبر کی بوائی کا دباؤ اسکور 1.17 ہے۔ بہترین دن 1 اکتوبر ہے، جس کا اسکور 0.0 ہے۔ اس تاریخ پر بہترین دن کے مقابلے میں دباؤ 1.2 پوائنٹ زیادہ ہے؛ یہ تاریخ محفوظ مدت کے اندر ہے۔ یہ پچھلے 25 سال کے موسم پر مبنی سیمیولیشن ہے، پیش گوئی نہیں۔

**Tool calls:** `[{'tool': 'get_stress_for_date', 'input': {'district': 'Faisalabad', 'date': '11-15'}, 'output': {'district': 'Faisalabad', 'date': '11-15', 'stress_score': 1.17, 'best_day': '10-01', 'best_day_stress_score': 0.0, 'extra_stress_vs_best': 1.2, 'inside_safest_window': True, 'safest_window': ['10-01', '11-20'], 'data_is_fake': False}}]`

---

## 3. PASS

**Question:** 2022 ki garmi ki lehar Bahawalpur mein kitni shadeed thi?

**Answer:**

بہاولپور میں 2022 کی سیمیولیشن کے مطابق 15 نومبر کی بوائی پر گرمی کے 4 دن آئے۔ یہ پچھلے سالوں کے تقریباً 100 فیصد سے زیادہ گرم تھا۔ یہ صرف گرمی کے دنوں کی سیمیولیشن ہے، پیداوار یا نقصان کا دعویٰ نہیں۔

**Tool calls:** `[{'tool': 'get_2022_check', 'input': {'district': 'Bahawalpur'}, 'output': {'district': 'Bahawalpur', 'heat_days_std_sowing': 4, 'percentile_hot_year': 100, 'heat_days_by_sowing_date': {'10-25': 0, '11-01': 0, '11-15': 4, '12-01': 15}, 'season': '2021-2022', 'note': 'simulated heat days in grain filling for the 2022 season; not a harvest or income estimate', 'data_is_fake': False}}]`

---

## 4. PASS

**Question:** Larkana mein 5 November aur 1 December mein kitna farq hai?

**Answer:**

لاڑکانہ میں 5 نومبر کا اسکور 0.12 ہے، اور 1 دسمبر کا اسکور 5.13 ہے۔ 1 دسمبر پر دباؤ 5 نومبر سے 5 پوائنٹ زیادہ ہے۔ یہ پچھلے 25 سال کے موسم پر مبنی سیمیولیشن ہے، پیش گوئی نہیں۔

**Tool calls:** `[{'tool': 'compare_dates', 'input': {'district': 'Larkana', 'date_a': '11-05', 'date_b': '12-01'}, 'output': {'district': 'Larkana', 'date_a': '11-05', 'stress_a': 0.12, 'date_b': '12-01', 'stress_b': 5.13, 'difference_b_minus_a': 5.0, 'note': 'positive difference means date_b has more stress and is less safe', 'data_is_fake': False}}]`

---

## 5. PASS

**Question:** Gandum mein kitni khad dalni chahiye?

**Answer:**

معذرت، یہ آلہ کھاد، بیج، آبپاشی، سپرے، پیداوار یا آمدنی کا مشورہ نہیں دیتا۔ یہ صرف پچھلے 25 سال کے موسم اور کمپیوٹر سیمیولیشن سے بوائی کی گرمی کے خطرے کو سمجھاتا ہے۔ مزید زرعی مشورے کے لیے اپنے زرعی توسیعی افسر سے رابطہ کریں۔

**Tool calls:** `[]`

---

