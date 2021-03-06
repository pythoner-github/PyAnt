<?xml version='1.0' encoding='utf-8'?>

<patches version='2.0'>
  <!--
    一个补丁申请单中, 可以填写多个补丁
    当有一个补丁制作失败时, 所有补丁都算做失败

    如果需要自动制作增量脚本, 需要按如下方式进行操作:
    1) 增量脚本打包为标准的zip格式, 并且文件名与补丁申请单名称相同
    2) 在patch节点, 增加一个script属性, 取值为ems, nms, lct, upgrade或service(可填写多个值, 用逗号分隔)
    3) 将补丁申请单和zip文件放在同一目录下

    示例:
      <patch name='U31R22_PLATFORM' script='ems, nms'>

    如果需要在指定操作系统上打补丁, 需要按如下方式进行操作:
    1) 在patch节点, 增加一个os属性, 取值为windows, linux或solaris(可填写多个值, 用逗号分隔)
    2) 如果没有os属性, 则在所有平台上打补丁

    示例:
      <patch name='U31R22_PLATFORM' os='windows, linux'>
  -->
  <patch name='U31R22_PLATFORM'>
    <!--
      删除信息(可选)

      name  : 需要在编译环境中删除的文件或目录
    -->
    <delete>
      <attr name='code/core/explorer/src/com/zte/ican/explorer/api'/>
    </delete>

    <!--
      变更信息(可选)

      name  : 需要变更的文件或目录
    -->
    <source>
      <attr name='code/utils/util/src/com/zte/ican/util/TDebugPrn.java'/>
      <attr name='code_c/core/embinit/src'/>
    </source>

    <!--
      编译信息(可选)

      name  : 需要执行命令的目录
      clean : 是否执行clean, c++默认为false, java默认为true
    -->
    <compile>
      <attr name='code/core/explorer'/>
      <attr name='code_c/core/embinit/lib' clean='true'/>
    </compile>

    <!-- 发布信息(可选) -->
    <deploy>
      <!--
        发布到版本(可选)

        name  : 源文件或目录, 必须以code/build/output, code_c/build/output或installdisk开头
        text  : 目的路径, 如不写, 则为output后的部分(installdisk开头必须写目的路径)
        type  : 版本类型(ems, nms, lct, upgrade(独立升级工具), service), 多个类型以逗号隔开, 默认为ems

        * 包含ums-nms的为nms, 包含ums-lct的为lct, 此时type值无效
      -->
      <deploy>
        <attr name='code/build/output/ums-lct/procs/ppus/bnplatform.ppu/platform-api.pmu/bn-platform-util.par/ican-util.jar'/>
        <attr name='code/build/output/ums-nms/procs/ppus/bnplatform.ppu/platform-api.pmu/bn-platform-util.par/ican-util.jar'/>
        <attr name='code/build/output/ums-client/procs/ppus/bnplatform.ppu/platform-api.pmu/bn-platform-util.par/ican-util.jar' type='ems, nms'/>
        <attr name='code/build/output/ums-server/procs/ppus/bnplatform.ppu/platform-api.pmu/bn-platform-util.par/ican-util.jar' type='ems, nms, lct'/>
        <attr name='code_c/build/output/ums-server/procs/ppus/bnplatform.ppu/platform-api-c.pmu/emb/usf-emb-init.dll' type='ems, nms, lct'/>
        <attr name='installdisk/bn_ptn/install/plugins/installdb/bn/impl/uif-3-ptn-jdbc.xml' type='ems'>install/plugins/installdb/bn/impl/uif-3-ptn-jdbc.xml</attr>
      </deploy>

      <!--
        从版本删除(可选)

        name  : 需要从版本中删除的文件或目录
        type  : 版本类型(ems, nms, lct, upgrade, service), 多个类型以逗号隔开, 默认为ems
      -->
      <delete>
        <attr name='ums-server/procs/ppus/bnplatform.ppu/platform-api-c.pmu/dll/dbutils.dll' type='ems, nms, lct'/>
      </delete>
    </deploy>

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
      <attr name='变更版本'>12.18.10 -B13</attr>
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
      <attr name='抄送人员'>万一鸣/00100277</attr>
    </info>
  </patch>
</patches>