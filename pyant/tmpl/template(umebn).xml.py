<?xml version='1.0' encoding='utf-8'?>

<patches version='2.0'>
  <!--
    一个补丁申请单中, 可以填写多个补丁
    当有一个补丁制作失败时, 所有补丁都算做失败
  -->
  <patch name='umebn'>
    <!--
      变更信息(可选)

      name  : 需要变更的文件或目录
    -->
    <source>
      <attr name='support/platform'/>
    </source>

    <!--
      补丁信息(必填)

      提交人员, 变更版本, 变更类型, 变更描述, 关联故障, 影响分析, 自测结果, 开发经理, 抄送人员为必填项
        - 提交人员: 姓名/工号
        - 变更类型: 故障, 需求, 优化
        - 变更描述: 最少10个汉字或20个英文字母
        - 关联故障: 故障, 需求或优化ID, 必须为数字
        - 变更来源: 不能为空
        - 开发经理: 姓名/工号
        - 抄送人员: 姓名/工号(可以多人, 用逗号分隔)

      * 系统会发送邮件给提交人员, 并抄送开发经理和抄送人员, 请保证工号填写正确(邮件地址为 工号@zte.com.cn)
    -->
    <info>
      <attr name='提交人员'>苟亚斌/10067748</attr>
      <attr name='变更版本'>V2.10.00.B01</attr>
      <attr name='变更类型'>故障</attr>
      <attr name='变更描述'>变更描述, 变更描述最少10个汉字或20个英文字母</attr>
      <attr name='关联故障'>613002089187</attr>
      <attr name='影响分析'>影响分析</attr>
      <attr name='依赖变更'/>
      <attr name='走查人员'>欧雪刚/10032547</attr>
      <attr name='走查结果'>走查通过</attr>
      <attr name='自测结果'>自测结果</attr>
      <attr name='变更来源'>不能为空</attr>
      <attr name='开发经理'>欧雪刚/10032547</attr>
      <attr name='抄送人员'>张新平/10021895</attr>
    </info>
  </patch>
</patches>