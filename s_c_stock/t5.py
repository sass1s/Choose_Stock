s0 = ['41.90', '41.90', '42.04', '41.95', '42.11', '41.73', '42.48', '42.47', '42.25', '42.77', '41.98', '41.00', '41.45', '40.62', '40.13', '40.01', '40.64', '41.21', '41.98', '41.79', '42.37', '42.37', '43.58', '43.54', '43.14', '42.36', '41.56', '40.40', '40.61', '40.60', '39.95', '40.82', '40.64', '40.49', '39.79', '39.06', '39.04', '38.51', '37.86', '37.69', '38.32', '39.40', '39.88', '39.50', '39.23', '39.24', '39.90', '39.47', '39.54', '39.54', '39.54', '39.66', '38.54', '39.30', '40.39', '39.62', '39.91', '39.42', '39.44', '39.54', '42.66', '41.500', '41.200', '41.130', '40.850', '41.450', '42.280', '42.030', '45.380', '46.700']

y = []
for x in range(len(s0)-1):
    z = (float(s0[x+1])-float(s0[x]))/float(s0[x])
    y.append('{:.2%}'.format(z))
