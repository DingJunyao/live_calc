# backend/tests/services/test_translate_task.py
"""TranslateTask 老路径测试已被 Task 7 引擎替换重构。

原测试针对 ``translate_batch`` 分批串行路径（mock ``get_translator``），
Task 7 把引擎换成 ``LangChainRunner`` + ``run_agent_loop(unattended=True)``
后该 mock 不再存在。新引擎的「只译 pending / 不动 done」语义已由
``tests/translate/test_translate_task_agent.py`` 完整覆盖（fdc=3 原 done
行 translate_status/description_zh 不变），此处保留占位避免导入空模块。
"""
