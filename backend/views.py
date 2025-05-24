from django.http import HttpResponse, StreamingHttpResponse, JsonResponse, HttpResponseNotFound
import subprocess
import json
import re
import ast
import os
import time
from pathlib import Path


KEY_PATH = '/home/jasper/Developer/PyCharm/id_rsa_hust_server'
SERVER84 = 'jinjm@192.168.165.231'
SERVER86 = 'jinjm@192.168.165.232'

def hello(request):
    print("debug: hello")
    return HttpResponse("Hello world ! ")


"""
algo参数：kclique, pagerank, gcn
dataset参数：rmat16, rmat17, rmat18, rmat19, rmat20
"""
def part1(request, algo, dataset):
    print(f'[part1_execute] 请求算法：{algo} 数据集: {dataset}')

    # 构建SSH命令（添加stdbuf -oL确保行缓冲）
    cmd = f'ssh -i {KEY_PATH} -p 22222 {SERVER84} "stdbuf -oL /usr/bin/python3 -u /home/jinjm/local/cmd/run_part1.py --algo {algo} --dataset {dataset}"'
    print(f'[part1_execute] 执行命令: {cmd}')
    
    try:
        # 流式执行命令
        response = StreamingHttpResponse(
            command_stream_generator(cmd),
            content_type='text/event-stream',
        )
        response['Cache-Control'] = 'no-cache'
        return response
        
    except Exception as e:
        print(f'[part1_execute] 错误: {str(e)}')
        return JsonResponse(
            {"status": 500, "error": str(e)},
            status=500
        )


def get_part1_result(request, algo, dataset):
    """获取part1执行结果"""
    print('[get_part1_result] 请求结果')
    
    # 固定结果文件路径
    result_file = f'/home/jinjm/local/result_{algo}_{dataset}.json'
    cmd = f'ssh -i {KEY_PATH} -p 22222 {SERVER84} "cat {result_file}"'
    
    try:
        print(f'[get_part1_result] 获取结果: {cmd}')
        result = subprocess.check_output(cmd, shell=True, stderr=subprocess.PIPE, text=True)
        
        # 直接返回远程文件内容（假设已经是合法JSON）
        return JsonResponse(json.loads(result))
        
    except subprocess.CalledProcessError as e:
        print(f'[get_part1_result] 命令执行失败: {e.stderr}')
        return JsonResponse(
            {"status": 500, "error": "获取结果失败", "details": e.stderr},
            status=500
        )
    except json.JSONDecodeError:
        print('[get_part1_result] JSON解析失败')
        return JsonResponse(
            {"status": 500, "error": "结果格式无效"},
            status=500
        )
    except Exception as e:
        print(f'[get_part1_result] 未知错误: {str(e)}')
        return JsonResponse(
            {"status": 500, "error": str(e)},
            status=500
        )



# CACHE_DIR = Path("/home/jasper/part3_cache")
# CACHE_DIR.mkdir(exist_ok=True, parents=True)

# def get_cache_path(framework, algo):
#     """获取缓存文件路径"""
#     return CACHE_DIR / f"{framework}_{algo}.json"


# 获取当前项目根目录（假设 part3_cache 和 backend 同级）
PROJECT_ROOT = Path(__file__).parent.parent  # backend -> 项目根目录
CACHE_DIR = PROJECT_ROOT / "part3_cache"
CACHE_DIR.mkdir(exist_ok=True, parents=True)

def get_cache_path(framework, algo):
    """获取缓存文件路径"""
    return CACHE_DIR / f"{framework}_{algo}.json"



def command_stream_generator(cmd):
    print(f"[stream_gen] 执行命令: {cmd}")
    process = subprocess.Popen(
        cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
    )

    try:
        print("[stream_gen] 进程已启动，开始读取输出...")
        while True:
            line_bytes = process.stdout.readline()
            if not line_bytes:
                if process.poll() is not None:
                    break
                continue

            try:
                line = line_bytes.decode('utf-8').rstrip('\n')
            except UnicodeDecodeError as e:
                line = f"[解码错误] {str(e)}"
                print(f"[stream_gen] {line}")

            print(f"[stream_gen] 准备发送整行内容: {line}")
            
            # 直接发送完整行（保留换行符）
            event_data = f"data: {line}\n\n"
            yield event_data
            time.sleep(0.1)
            print(f"[stream_gen] 已发送完整行数据")

            # 保留原换行逻辑（可选）
            # yield "data: </br>\n\n"
            # time.sleep(0.1)  # 如果仍需间隔

        print("[stream_gen] 流式输出完成")
        yield "data: [done]\n\n"

    except Exception as e:
        print(f"[stream_gen] 发生异常: {str(e)}")
        yield "data: [error]\n\n"
    finally:
        if process.poll() is None:
            process.terminate()
            print("[stream_gen] 已终止子进程")


def part3_cgafile(request, framework, algo, rw):
    print("[part3_cgafile] 收到请求")
    # 构建SSH命令
    cmd = f'ssh -i {KEY_PATH} -p 22222 {SERVER86} "stdbuf -oL /home/jinjm/anaconda3/bin/python -u /home/jinjm/local/run_part3.py --fw fw1 --op readfile --algorithm {algo}"'
    print("执行命令:", cmd)

    try:
        # 执行命令并捕获输出
        process = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # 读取标准输出和错误
        stdout, stderr = process.communicate()
        
        # 检查返回码
        if process.returncode != 0:
            return JsonResponse({
                'status': 'error',
                'message': f'命令执行失败 (返回码: {process.returncode})',
                'error': stderr.strip(),
                'command': cmd
            }, status=500)
        
        # 成功返回
        return JsonResponse({
            'status': 'success',
            'framework': framework,
            'algorithm': algo,
            'operation': 'readfile',
            'content': stdout.strip(),
            'command': cmd
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': '执行过程中发生异常',
            'error': str(e),
            'command': cmd
        }, status=500)



def part3(request, framework, algo):
    print("[part3] 收到请求")
    
    # 构建SSH命令
    cmd = f'ssh -i {KEY_PATH} -p 22222 {SERVER86} "stdbuf -oL /home/jinjm/anaconda3/bin/python -u /home/jinjm/local/run_graph_computing.py --fw {framework} --{"data" if framework == "3" else "algo"} {algo}"'
    print("执行命令:", cmd)
    
    try:
        # 流式执行命令
        response = StreamingHttpResponse(
            command_stream_generator(cmd),
            content_type='text/event-stream',
        )
        response['Cache-Control'] = 'no-cache'
        
        return response
        
    except Exception as e:
        print(f"[part3] 响应创建失败: {str(e)}")
        return JsonResponse(
            {"status": 500, "error": str(e)},
            status=500
        )


def get_part3_result(request, framework, algo):
    """
    获取已缓存的JSON结果
    """
    print(f"[get_part3_result] 获取结果: {framework}/{algo}")
    
    try:
        # 从远程服务器获取结果
        json_cmd = f'ssh -i {KEY_PATH} -p 22222 {SERVER86} "cat /home/jinjm/local/result.json"'
        result = subprocess.check_output(json_cmd, shell=True)
        json_data = json.loads(result)
        
        # 缓存到本地文件
        cache_file = get_cache_path(framework, algo)
        with open(cache_file, 'w') as f:
            json.dump(json_data, f, indent=2)
        print(f"[get_part3_result] JSON结果已缓存到 {cache_file}")
        
        return JsonResponse(json_data)
        
    except subprocess.CalledProcessError as e:
        print(f"[get_part3_result] 获取JSON结果失败: {str(e)}")
        return JsonResponse(
            {"status": 500, "error": str(e)},
            status=500
        )
    except json.JSONDecodeError:
        print("[get_part3_result] JSON解析错误")
        return JsonResponse(
            {"status": 500, "error": "无效的JSON格式"},
            status=500
        )
    except Exception as e:
        print(f"[get_part3_result] 未知错误: {str(e)}")
        return JsonResponse(
            {"status": 500, "error": str(e)},
            status=500
        )


def part3data(request, framework, algo, data_type):
    """获取缓存数据中的特定字段"""
    print(f"[part3data] 请求数据: {framework}/{algo}/{data_type}")
    
    try:
        # 1. 检查缓存文件是否存在
        cache_file = get_cache_path(framework, algo)
        if not os.path.exists(cache_file):
            return JsonResponse(
                {"status": 404, "error": "缓存文件不存在，请先执行part3接口"},
                status=404
            )
        
        # 2. 读取缓存文件
        with open(cache_file, 'r') as f:
            cached_data = json.load(f)
        
        # 3. 检查请求的数据类型是否有效
        valid_data_types = ["asm", "CGA", "GraphIR", "log", "MatrixIR", "pregel"]
        if data_type not in valid_data_types:
            return JsonResponse(
                {"status": 400, "error": f"无效的数据类型，有效类型为: {valid_data_types}"},
                status=400
            )
        
        # 4. 检查请求的数据是否存在
        if "data" not in cached_data or data_type not in cached_data["data"]:
            return JsonResponse(
                {"status": 404, "error": f"请求的数据类型 '{data_type}' 不存在于结果中"},
                status=404
            )
        
        # 5. 返回请求的数据
        return JsonResponse({
            "status": 200,
            "framework": framework,
            "algorithm": algo,
            "data_type": data_type,
            "data": cached_data["data"][data_type]
        })
        
    except json.JSONDecodeError:
        return JsonResponse(
            {"status": 500, "error": "缓存文件格式错误"},
            status=500
        )
    except Exception as e:
        return JsonResponse(
            {"status": 500, "error": f"服务器错误: {str(e)}"},
            status=500
        )


def part3_moni(request, algo):
    print("[part3] 收到请求")
    
    # 构建SSH命令
    cmd = cmd = f'ssh -i {KEY_PATH} -p 22222 {SERVER86} "stdbuf -oL bash /home/jinjm/local/run_graph_1.sh {algo}"'
    print("执行命令:", cmd)
    
    try:
        # 流式执行命令
        response = StreamingHttpResponse(
            command_stream_generator(cmd),
            content_type='text/event-stream',
        )
        response['Cache-Control'] = 'no-cache'
        
        return response
        
    except Exception as e:
        print(f"[part3] 响应创建失败: {str(e)}")
        return JsonResponse(
            {"status": 500, "error": str(e)},
            status=500
        )



def part3_moni2(request, algo):
    print("[part3] 收到请求")
    
    # 构建SSH命令
    cmd = cmd = f'ssh -i {KEY_PATH} -p 22222 {SERVER86} "stdbuf -oL bash /home/jinjm/local/run_graph_2.sh {algo}"'
    print("执行命令:", cmd)
    
    try:
        # 流式执行命令
        response = StreamingHttpResponse(
            command_stream_generator(cmd),
            content_type='text/event-stream',
        )
        response['Cache-Control'] = 'no-cache'
        
        return response
        
    except Exception as e:
        print(f"[part3] 响应创建失败: {str(e)}")
        return JsonResponse(
            {"status": 500, "error": str(e)},
            status=500
        )



def stream_test(request):
    print("[stream_test] 收到SSE请求")
    try:
        cmd = f'ssh -i {KEY_PATH} -p 22222 {SERVER84} "stdbuf -oL bash /home/jinjm/local/cmd/run_stream.sh"'
        response = StreamingHttpResponse(
            command_stream_generator(cmd),
            content_type='text/event-stream',
        )
        response['Cache-Control'] = 'no-cache'
        print("[stream_test] 流式响应准备就绪")
        return response
    except Exception as e:
        print(f"[stream_test] 响应创建失败: {str(e)}")
        raise


def read_log_file(request, filename):
    # 获取当前文件（views.py）的绝对路径目录（backend目录）
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 构建相对路径：backend -> 项目根目录 -> logfile -> 目标文件
    log_file_path = os.path.normpath(os.path.join(current_dir, '..', 'logfile', f"{filename}.log"))
        
    # 检查文件是否存在
    if not os.path.exists(log_file_path):
        return HttpResponseNotFound(f"Log file {filename}.log not found")
    
    # 检查是否为合法文件（防止目录遍历攻击）
    if not os.path.isfile(log_file_path):
        return HttpResponse("Invalid file path", status=400)
    
    try:
        # 读取文件内容
        with open(log_file_path, 'r') as f:
            content = f.read()
        
        # 返回文件内容
        return HttpResponse(content, content_type='text/plain')
    
    except Exception as e:
        # 处理读取错误
        return HttpResponse(f"Error reading file: {str(e)}", status=500)