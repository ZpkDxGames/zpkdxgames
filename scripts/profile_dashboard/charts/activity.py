from math import sqrt

def rolling(values,n=7):
    out=[]
    for i in range(len(values)):
        seg=values[max(0,i-n+1):i+1]; out.append(sum(seg)/len(seg))
    return out

def scaled(value,max_value,height):
    if max_value<=0:return 0
    return sqrt(max(0,value))/sqrt(max_value)*height