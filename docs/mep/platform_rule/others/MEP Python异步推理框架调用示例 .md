MEP Python异步推理框架调用示例
2022-01-26 14:26 由xxxxxx 创建，于 2026-04-15 11:35 由 xxxxxxxxxxx 最后修改。 内容存疑 点我
调用POD_IP的业务都不用看，看调用MSG的就行了

创建
创建--调用POD_IP返回结果：

# CREATE_POD_IP http://<pod_ip>:<pod_port>/sgp/<service_name>/infers/<service_version>/upredict/infers
# REQUEST:
{
   "data":{
       "reqData":[
          {
               "data":{
                   "taskId":"f3b11061-608b-4bc4-9e22-c4a2d8e74790",
                   "action":"create"
              },
               "version":"1.0"
          }
      ],
       "count":1
  },
   "meta":{
       "bId":"test",
       "flowId":"async",
       "uuId":"1502346942471"
  },
   "version":"1.2"
}
# Response
{
   "meta":{
       "bId":"test",
       "flowId":"async",
       "uuId":"1502346942471"
  },
   "result":{
       "code":0,
       "count":1,
       "des":"ok",
       "serviceName":"async_test",
       "serviceVersion":"2.0.0"
  },
   "version":"1.2"
}
创建--调用MSG返回结果：

# CREATE_MSG http://<msg_ip>:<msg_port>/service
# Request
{
   "version":"1.2",
   "meta":{
       "bId":"test",
       "flowId":"async",
       "uuId":"1502346942471"
  },
   "data":{
       "taskId":"ea72bf0b-66bc-4098-a93a-5df7a64911db",  # 必选参数
       "action":"create",  # 必选参数
       # 其下均为可选参数，可根据业务实际情况传递
       "basePath":"/opt/huawei/sfsmodel/mep",
       "fileInfo":[
          {
               "sourceImage":"00017160.jpg",
               "sourcePath":"/opt/huawei/sfsmodel/mep/sourcepath",
               "generatePath":"/opt/huawei/sfsmodel/mep/generatePath",
               "processSpec":[

              ]
          }
      ]
  }
}

# Response
{
   "version":"1.2",
   "meta":{
       "subId":"",
       "flowId":"async",
       "bId":"test",
       "uuId":"1502346942471",
       "interfaceID":"ABTest_MEP_001",
       "abtest":0
  },
   "experiment":{
       "expParams":"",
       "expDes":"",
       "expId":""
  },
   "result":{
       "code":"0",
       "des":"ok",
       "length":"0",
       "content":[

      ]
  },
   "expInfo":""
}
查询
查询--调用POD_IP返回结果：

# QUERY_POD_IP http://<pod_ip>:<pod_port>/sgp/<service_name>/infers/<service_version>/upredict/infers
# REQUEST
{
   "data":{
       "reqData":[
          {
               "data":{
                   "taskId":"bf210d34-4b1b-46b3-8d34-37a743860424",
                   "action":"query"
              },
               "version":"1.0"
          }
      ],
       "count":1
  },
   "meta":{
       "bId":"test",
       "flowId":"async",
       "uuId":"1502346942471"
  },
   "version":"1.2"
}

# Response
{
   "meta":{
       "bId":"test",
       "flowId":"async",
       "uuId":"1502346942471"
  },
   "result":{
       "code":0,
       "count":1,
       "des":"query task bf210d34-4b1b-46b3-8d34-37a743860424 success, task status is FINISHED ",
       "respData":[
          {
               "recommendResult":{
                   "code":"3",
                   "content":[
                      {
                           "des":"request data is missing."
                      }
                  ],
                   "des":"request data is missing.",
                   "length":0
              }
          }
      ],
       "serviceName":"async_test",
       "serviceVersion":"1.0.0"
  },
   "version":"1.2"
}


查询--调用MSG返回结果：

# QUERY_MSG http://<msg_ip>:<msg_port>/service
# Request
{
   "version":"1.2",
   "meta":{
       "bId":"test",
       "flowId":"async",
       "uuId":"1502346942471"
  },
   "data":{
       "taskId":"bf210d34-4b1b-46b3-8d34-37a743860424",
       "action":"query"
  }
}

# Response
{
   "version":"1.2",
   "meta":{
       "subId":"",
       "flowId":"async",
       "bId":"test",
       "uuId":"1502346942471",
       "interfaceID":"ABTest_MEP_001",
       "abtest":0
  },
   "experiment":{
       "expParams":"",
       "expDes":"",
       "expId":""
  },
   "result":{
       "code":"3",
       "des":"request data is missing.",
       "length":0,
       "content":[
          {
               "des":"request data is missing."
          }
      ]
  },
   "expInfo":""
}
取消
取消--调用POD_IP返回结果：

# CANCEL_POD_IP http://<pod_ip>:<pod_port>/sgp/<service_name>/infers/<service_version>/upredict/infers
# Request
{
   "data":{
       "reqData":[
          {
               "data":{
                   "taskId":"ab31c8f7-6d3b-4043-9512-88cff9da921c",
                   "action":"cancel"
              },
               "version":"1.0"
          }
      ],
       "count":1
  },
   "meta":{
       "bId":"test",
       "flowId":"async",
       "uuId":"1502346942471"
  },
   "version":"1.2"
}

# Response
{
   "meta":{
       "bId":"test",
       "flowId":"async",
       "uuId":"1502346942471"
  },
   "result":{
       "code":0,
       "count":1,
       "des":"ok",
       "serviceName":"async_test",
       "serviceVersion":"2.0.0"
  },
   "version":"1.2"
}


取消--调用MSG返回结果：

# CANCEL_MSG http://<msg_ip>:<msg_port>/service
# Request
{
   "version":"1.2",
   "meta":{
       "bId":"test",
       "flowId":"async",
       "uuId":"1502346942471"
  },
   "data":{
       "taskId":"65189803-f604-4cde-a062-ace71e800d23",
       "action":"cancel"
  }
}

# Response
{
   "version":"1.2",
   "meta":{
       "subId":"",
       "flowId":"async",
       "bId":"test",
       "uuId":"1502346942471",
       "interfaceID":"ABTest_MEP_001",
       "abtest":0
  },
   "experiment":{
       "expParams":"",
       "expDes":"",
       "expId":""
  },
   "result":{
       "code":"0",
       "des":"ok",
       "length":"0",
       "content":[

      ]
  },
   "expInfo":""
}
分享
添加收藏
点赞 0