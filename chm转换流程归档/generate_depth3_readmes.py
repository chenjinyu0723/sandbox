#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
README 生成辅助脚本 —— 第二步：为所有 depth-3 文件夹写入 README.md

依赖：先运行 extract_command_funcs.py 理解命令内容，
      或直接内联 get_func_lines 函数。

设计：根据文件夹名称关键词匹配预定义的类别描述，
      然后为每条命令写入一行功能简介。
"""

import os, re

base = r"C:\Users\chenjinyu\Desktop\机器学习\tmp\命令参考_文件夹"

def get_func_lines(filepath):
    """从命令文件中提取'命令功能'段的内容"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        in_func = False
        func_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped == '命令功能':
                in_func = True
                continue
            if in_func:
                if stripped in ('命令格式', '参数说明', '视图', '缺省级别', '使用指南', '使用实例'):
                    break
                if stripped:
                    func_lines.append(stripped)
        return ' '.join(func_lines)
    except:
        return ''

def categorize_folder(name, commands):
    """
    根据文件夹名称和命令内容生成该文件夹的用途描述。
    
    策略：关键词匹配 → 预定义模板。
    如果文件夹名称不能匹配任何关键词，返回泛化描述。
    """
    funcs = ' '.join([c['func'] for c in commands if c['func']]).lower()
    n = name.lower()
    
    # === 路由协议 ===
    if 'bgp' in n:
        return "BGP（边界网关协议）配置命令，包括BGP邻居管理、路由策略、路由反射器、联盟、MP-BGP、BGP FlowSpec、ADD-PATH等丰富功能。"
    if '静态路由' in n:
        return "IPv4和IPv6静态路由配置命令，用于配置和管理静态路由表项，包括默认路由、浮动静态路由、BFD联动等功能。"
    if 'is-is' in n:
        return "IS-IS（中间系统到中间系统）配置命令，用于IS-IS路由协议的配置，包括区域管理、邻居管理、路由策略、GR等功能。"
    if 'ospfv3' in n:
        return "OSPFv3（IPv6开放最短路径优先）配置命令，用于IPv6网络中的OSPF路由协议配置。"
    if 'ospf' in n:
        return "OSPF（开放最短路径优先）配置命令，包括区域管理、邻居管理、路由策略、Stub/NSSA区域、GR等功能。"
    if 'ripng' in n:
        return "RIPng（下一代RIP）配置命令，用于IPv6网络中的RIP路由协议配置。"
    if 'rip' in n and 'ripng' not in n:
        return "RIP（路由信息协议）配置命令，用于IPv4网络中的RIP路由协议配置。"
    if '路由策略' in n:
        return "路由策略配置命令，包括Route-Policy、AS-Path过滤器、Community过滤器、Extcommunity过滤器、IP前缀列表等路由控制功能。"
    if '路由管理' in n:
        return "路由管理配置命令，包括路由表管理、路由引入、路由聚合、路由选路策略、IP FRR、路由按需下发等功能。"
    
    # === ACL ===
    if 'acl6' in n:
        return "ACL6（IPv6访问控制列表）配置命令，用于创建和管理IPv6 ACL规则，包括基本ACL6、高级ACL6和用户ACL6。"
    if 'acl' in n:
        return "ACL（访问控制列表）配置命令，用于创建和管理ACL规则，包括基本ACL、高级ACL、二层ACL、用户ACL和基于ARP的ACL。"
    
    # === ARP/ND ===
    if 'arp安全' in n:
        return "ARP安全配置命令，用于防范ARP攻击，包括DAI、ARP表项固化、ARP报文限速、免费ARP控制、ARP防网关冲突等。"
    if 'arp' in n:
        return "ARP（地址解析协议）配置命令，包括静态/动态ARP表项管理、ARP探测、代理ARP、ARP-Ping等功能。"
    if 'nd snooping' in n:
        return "ND Snooping配置命令，用于IPv6邻居发现安全防护，管理ND绑定表，防范ND欺骗攻击。"
    if 'nd' in n:
        return "ND（邻居发现）配置命令，包括静态ND表项、ND代理、RA报文控制、ND探测等功能。"
    
    # === DHCP ===
    if 'dhcp snooping' in n:
        return "DHCP Snooping配置命令，用于DHCP安全防护，包括DHCP报文过滤、绑定表管理、DHCP限速、Option82处理等。"
    if 'dhcpv4' in n:
        return "DHCPv4配置命令，用于DHCP服务器和DHCP中继的配置，包括地址池管理、地址分配策略、Option配置、BOOTP支持等。"
    if 'dhcpv6' in n:
        return "DHCPv6配置命令，用于IPv6 DHCP服务器和中继配置，包括IPv6地址前缀分配、DNS配置、PD前缀委托等。"
    
    # === IPv4/IPv6 基础 ===
    if 'ipv4基础' in n:
        return "IPv4基础配置命令，包括IP地址配置、ARP代理、ICMP属性、TCP属性、PMTU等IPv4协议栈基础功能。"
    if 'ipv6 ra guard' in n:
        return "IPv6 RA Guard配置命令，用于防范非法RA报文攻击，保护IPv6网络安全。"
    if 'ipv6基础' in n:
        return "IPv6基础配置命令，包括IPv6地址配置、ND协议、ICMPv6、PMTU等IPv6协议栈基础功能。"
    
    # === DNS ===
    if 'dns' in n:
        return "DNS配置命令，用于DNS服务器和DNS代理配置，包括静态/动态域名解析、DNS缓存管理、DDNS等功能。"
    
    # === SAVI ===
    if 'savi' in n:
        return "SAVI（源地址验证改进）配置命令，用于IPv6源地址验证，防止源地址欺骗攻击。"
    
    # === 负载分担 ===
    if '负载分担' in n:
        return "负载分担配置命令，包括ECMP负载分担策略、Hash算法配置、本地优先转发等功能。"
    
    # === 应用识别 ===
    if '应用识别' in n:
        return "应用识别配置命令，用于配置和管理SA应用识别功能，包括自定义应用、应用签名管理等。"
    
    # === 组播 ===
    if 'igmp' in n:
        return "IGMP（互联网组管理协议）配置命令，用于IPv4组播组成员管理，包括IGMP Snooping、SSM Mapping、IGMP限速等。"
    if 'mld' in n:
        return "MLD（组播侦听者发现协议）配置命令，用于IPv6组播组成员管理，包括MLD Snooping、SSM Mapping等。"
    if 'msdp' in n:
        return "MSDP（组播源发现协议）配置命令，用于跨PIM-SM域的组播源信息传递。"
    if 'pim' in n and 'ipv6' in n:
        return "IPv6 PIM（协议无关组播）配置命令，用于IPv6组播路由，包括PIM-SM、PIM-DM、PIM-SSM等模式。"
    if 'pim' in n:
        return "PIM（协议无关组播）配置命令，用于IPv4组播路由，包括PIM-SM、PIM-DM、PIM-SSM等模式。"
    if '组播' in n and '二层' in n and 'ipv6' in n:
        return "二层组播IPv6配置命令，用于IPv6二层网络中的组播功能，包括MLD Snooping策略、组播VLAN等。"
    if '组播' in n and '二层' in n:
        return "二层组播配置命令，用于二层网络中的组播功能，包括IGMP Snooping策略、组播VLAN、组播快速离开等。"
    if '组播路由' in n and 'ipv6' in n:
        return "IPv6组播路由管理配置命令，包括IPv6组播路由表管理、RPF检查、组播边界等功能。"
    if '组播路由' in n and 'ipv4' in n:
        return "IPv4组播路由管理配置命令，包括组播路由表管理、RPF检查、组播边界、组播负载分担等功能。"
    
    # === MPLS ===
    if 'ldp' in n:
        return "MPLS LDP（标签分发协议）配置命令，用于MPLS网络中标签的分配与管理。"
    if 'te' in n:
        return "MPLS TE（流量工程）配置命令，用于MPLS流量工程隧道的建立与管理。"
    if 'mpls qos' in n:
        return "MPLS QoS配置命令，用于MPLS网络中的QoS功能，包括MPLS EXP优先级映射、MPLS流量策略等。"
    
    # === QoS ===
    if 'mqc' in n:
        return "MQC（模块化QoS命令行）配置命令，用于基于流分类的QoS策略配置，包括流分类、流行为、流策略的定义与应用。"
    if '报文重定向' in n:
        return "报文重定向配置命令，用于将匹配特定条件的报文重定向到指定接口或下一跳。"
    if '接口限速' in n:
        return "接口限速配置命令，用于接口级别的流量速率限制，包括CAR和LR限速。"
    if '流量监管' in n:
        return "流量监管和流量整形配置命令，包括CAR流量监管、GTS流量整形、共享CAR等功能。"
    if '流量统计' in n:
        return "流量统计配置命令，用于流策略的报文统计功能配置。"
    if '体验保障' in n:
        return "体验保障配置命令，用于基于应用的网络体验质量保障。"
    if '拥塞避免' in n or '拥塞管理' in n:
        return "拥塞避免和拥塞管理配置命令，包括WRED、尾丢弃、队列调度（PQ/WRR/DRR/WFQ）、队列拥塞监控等功能。"
    if '优先级映射' in n:
        return "优先级映射配置命令，用于配置报文优先级与内部优先级之间的映射关系。"
    
    # === SR ===
    if 'segment routing' in n:
        return "Segment Routing IPv6（SRv6）配置命令，用于IPv6段路由的配置。"
    
    # === VPN ===
    if 'evpn' in n:
        return "EVPN（以太网虚拟专用网络）配置命令，包括EVPN实例、EVPN路由、多归属、MAC路由通告等。"
    if 'gre' in n:
        return "GRE（通用路由封装）配置命令，用于GRE隧道的创建与管理。"
    if 'l3vpn' in n and 'ipv6' in n:
        return "IPv6 L3VPN配置命令，用于MPLS/BGP三层VPN的IPv6场景配置。"
    if 'l3vpn' in n:
        return "IPv4 L3VPN配置命令，用于MPLS/BGP三层VPN的IPv4场景配置。"
    if 'vpls' in n:
        return "VPLS（虚拟专用局域网服务）配置命令，用于点到多点二层VPN的配置。"
    if 'vpws' in n:
        return "VPWS（虚拟专用线路服务）配置命令，用于点到点二层VPN的配置。"
    if '隧道管理' in n:
        return "隧道管理配置命令，包括隧道策略、隧道选择器、隧道统计等功能。"
    
    # === VXLAN ===
    if 'vxlan' in n:
        return "VXLAN（虚拟可扩展局域网）配置命令，用于VXLAN网络的配置，包括VXLAN隧道、VNI管理、BD映射、分布式网关等。"
    
    # === WLAN ===
    if 'ap管理' in n:
        return "AP管理配置命令，用于无线接入点的管理，包括AP上线、AP认证、AP配置下发、AP重启、AP分组等功能。"
    if 'capwap' in n:
        return "CAPWAP（无线接入点控制与配置协议）配置命令，用于AC与AP之间的CAPWAP隧道管理。"
    if 'hotspot' in n:
        return "Hotspot2.0配置命令，用于Passpoint/Hotspot2.0无线热点的配置。"
    if 'ssid' in n:
        return "SSID管理配置命令，用于无线网络的SSID创建与管理。"
    if 'wlan qos' in n:
        return "WLAN QoS配置命令，用于无线网络的QoS功能，包括WMM、用户限速、流量策略等。"
    if 'wlan安全' in n:
        return "WLAN安全配置命令，用于无线网络的安全功能，包括WPA/WPA2/WPA3认证、加密算法等。"
    if 'wlan可靠性' in n:
        return "WLAN可靠性配置命令，用于无线网络的可靠性功能。"
    if 'wlan逃生' in n:
        return "WLAN逃生配置命令，用于AC离线时AP的本地转发逃生功能配置。"
    if 'wlan用户管理' in n:
        return "WLAN用户管理配置命令，用于无线用户的管理，包括用户隔离、黑白名单、用户老化等。"
    if 'wlan运维监控' in n:
        return "WLAN运维监控配置命令，用于无线网络的运维监控。"
    if 'wlan组播' in n:
        return "WLAN组播配置命令，用于无线网络中的组播功能。"
    if '零漫游' in n:
        return "零漫游分布式Wi-Fi配置命令，用于分布式Wi-Fi零漫游方案的配置。"
    if '漫游' in n:
        return "漫游配置命令，用于WLAN用户漫游功能配置，包括快速漫游、智能漫游、PMK缓存等。"
    if '射频资源' in n:
        return "射频资源管理配置命令，用于无线射频资源的管理，包括信道管理、功率管理、射频调优等。"
    if '无线定位' in n:
        return "无线定位配置命令，用于基于Wi-Fi的无线设备定位功能。"
    if '物联网' in n:
        return "物联网插卡配置命令，用于AP上物联网插卡的管理。"
    
    # === 安全 ===
    if '本机防攻击' in n:
        return "本机防攻击配置命令，用于保护设备CPU免受各种攻击报文的冲击。"
    if '端口安全' in n:
        return "端口安全配置命令，用于限制端口学习MAC地址的数量，防止MAC地址泛洪攻击。"
    if '风暴抑制' in n:
        return "风暴抑制配置命令，用于抑制广播、未知组播和未知单播风暴。"
    if 'ssh' in n:
        return "SSH（安全外壳）配置命令，用于SSH服务器和客户端配置。"
    if 'ssl' in n:
        return "SSL（安全套接层）配置命令，用于SSL/TLS策略配置。"
    if 'https' in n:
        return "HTTPS配置命令，用于HTTP/HTTPS服务的配置。"
    if 'macsec' in n:
        return "MACsec（MAC安全）配置命令，用于二层链路加密。"
    if 'ipsg' in n:
        return "IPSG（IP源地址防护）配置命令，用于IP源地址验证。"
    if 'urpf' in n:
        return "URPF（单播反向路径转发）配置命令，用于防范源地址欺骗攻击。"
    if 'pki' in n:
        return "PKI（公钥基础设施）配置命令，用于证书管理。"
    if 'keychain' in n:
        return "Keychain配置命令，用于密钥链管理。"
    if 'gtsm' in n:
        return "GTSM（通用TTL安全机制）配置命令，用于通过TTL值防范攻击。"
    if 'pppoe' in n:
        return "PPPoE+配置命令，用于PPPoE中间代理功能。"
    if 'fips' in n:
        return "FIPS（联邦信息处理标准）配置命令。"
    if 'hips' in n:
        return "HIPS（主机入侵防御系统）配置命令。"
    if 'dim' in n:
        return "DIM（动态完整性度量）配置命令。"
    if '可信系统' in n:
        return "可信系统配置命令，用于设备可信计算和可信启动功能。"
    if '远程证明' in n:
        return "远程证明配置命令，用于设备身份的远程证明和安全验证。"
    if 'ase' in n:
        return "ASE（应用安全引擎）配置命令。"
    if '安全风险查询' in n:
        return "安全风险查询配置命令。"
    if '弱密码' in n:
        return "弱密码字典维护配置命令。"
    if '业务与管理隔离' in n:
        return "业务与管理隔离配置命令。"
    if '二层流量限制' in n:
        return "二层流量限制配置命令。"
    
    # === 基础配置 ===
    if 'ztp' in n:
        return "ZTP（零接触配置）配置命令，用于设备的自动部署和零接触上线。"
    if 'web' in n:
        return "登录设备Web界面配置命令，用于Web网管服务器的配置。"
    if '命令行界面' in n:
        return "登录设备命令行界面配置命令，用于CLI登录方式的配置。"
    if '配置文件管理' in n:
        return "配置文件管理配置命令，用于设备配置文件的保存、备份、恢复、配置回退等。"
    if '首次登录' in n:
        return "首次登录设备配置命令，用于设备初始化和基础CLI操作。"
    if '文件系统管理' in n:
        return "文件系统管理配置命令，用于设备文件系统的操作。"
    
    # === 接口管理 ===
    if '串口透传' in n:
        return "串口透传配置命令。"
    if '端口隔离' in n:
        return "端口隔离配置命令，用于同一VLAN内端口之间的二层隔离。"
    if '接口基础' in n:
        return "接口基础配置命令，用于物理接口的基本属性配置。"
    if '逻辑接口' in n:
        return "逻辑接口配置命令，用于逻辑接口的配置。"
    if '以太网接口' in n:
        return "以太网接口配置命令，用于以太网接口的物理属性配置。"
    
    # === 以太网交换 ===
    if 'erps' in n:
        return "ERPS（以太网环保护切换）配置命令，用于环网保护。"
    if 'eth-trunk' in n:
        return "Eth-Trunk配置命令，用于链路聚合功能。"
    if 'gvrp' in n:
        return "GVRP（GARP VLAN注册协议）配置命令，用于VLAN的动态注册和注销。"
    if 'loopback detection' in n:
        return "Loopback Detection配置命令，用于检测和防范网络中的环路。"
    if 'mac' in n and 'macsec' not in n:
        return "MAC配置命令，用于MAC地址表管理。"
    if 'sep' in n:
        return "SEP（智能以太保护）配置命令，用于环网保护和快速收敛。"
    if 'stp' in n or 'rstp' in n or 'mstp' in n:
        return "STP/RSTP/MSTP配置命令，用于生成树协议，防止二层环路。"
    if 'vbst' in n:
        return "VBST（基于VLAN的生成树）配置命令。"
    if 'vcmp' in n:
        return "VCMP（VLAN集中管理协议）配置命令。"
    if 'vlan' in n:
        return "VLAN配置命令，用于VLAN的创建、管理和端口加入。"
    if '二层协议透明传输' in n:
        return "二层协议透明传输配置命令，用于跨运营商网络的二层协议报文透传。"
    
    # === 可靠性 ===
    if 'bfd' in n:
        return "BFD（双向转发检测）配置命令，用于快速检测链路故障。"
    if 'cfm' in n:
        return "CFM（连通性故障管理）配置命令，符合IEEE 802.1ag标准。"
    if 'dldp' in n:
        return "DLDP（设备链路检测协议）配置命令，用于检测单向链路故障。"
    if 'efm' in n:
        return "EFM（以太网故障管理）配置命令，符合IEEE 802.3ah标准。"
    if 'hsr' in n:
        return "HSR（高可用性无缝冗余）配置命令，用于工业网络高可靠性通信。"
    if 'mac swap' in n:
        return "MAC SWAP环回测试配置命令。"
    if 'm-lag' in n:
        return "M-LAG（多机链路聚合）配置命令，用于跨设备的链路聚合。"
    if 'monitor link' in n:
        return "Monitor Link配置命令，用于接口联动功能。"
    if 'smart link' in n:
        return "Smart Link配置命令，用于双上行组网中的链路冗余备份。"
    if 'vrrp6' in n:
        return "VRRP6配置命令，用于IPv6网络的虚拟路由冗余协议。"
    if 'vrrp' in n:
        return "VRRP（虚拟路由冗余协议）配置命令，用于IPv4网络的网关冗余。"
    if 'y.1731' in n:
        return "Y.1731配置命令，用于以太网性能监控，符合ITU-T Y.1731标准。"
    if '框内高可靠' in n:
        return "框内高可靠配置命令，用于主控板和交换网板的冗余备份和故障倒换。"
    
    # === 系统管理 ===
    if '1588v2' in n or 'ptp' in n:
        return "1588v2（PTP）配置命令，用于精密时钟同步协议。"
    if 'license' in n:
        return "License配置命令，用于设备许可证管理。"
    if 'lldp' in n:
        return "LLDP（链路层发现协议）配置命令，用于邻居设备发现和拓扑管理。"
    if 'netconf' in n:
        return "NETCONF配置命令，用于NETCONF网管协议的配置。"
    if 'ntp' in n:
        return "NTP（网络时间协议）配置命令，用于设备时间同步。"
    if 'ops' in n:
        return "OPS（开放可编程系统）配置命令，用于设备可编程性管理。"
    if 'poe' in n:
        return "PoE（以太网供电）配置命令，用于PoE供电管理。"
    if 'restconf' in n:
        return "RESTCONF配置命令，用于RESTCONF协议的配置。"
    if 'rmon' in n:
        return "RMON（远程网络监控）配置命令。"
    if 'snmp' in n:
        return "SNMP（简单网络管理协议）配置命令。"
    if 'ual' in n:
        return "UAL（用户接入位置）配置命令。"
    if '故障管理' in n:
        return "故障管理配置命令，用于设备的告警管理。"
    if '监控口' in n:
        return "监控口配置命令，用于工业交换机监控输入输出接口的配置。"
    if '节能管理' in n:
        return "节能管理配置命令，用于设备节能功能。"
    if '升级维护' in n:
        return "升级维护配置命令，用于设备软件升级、补丁管理、系统重启等。"
    if '特征库升级' in n:
        return "特征库升级配置命令，用于安全特征库的在线升级管理。"
    if '网络助手' in n:
        return "网络助手配置命令，用于极简园区网络中的整网自动化管理。"
    if '系统时间' in n:
        return "系统时间配置命令，用于设备系统时间的设置。"
    if '信息管理' in n:
        return "信息管理配置命令，用于设备日志和诊断信息的管理。"
    if '性能管理' in n:
        return "性能管理配置命令，用于设备性能数据的统计和上送。"
    if '硬件管理' in n:
        return "硬件管理配置命令，用于设备硬件管理。"
    if '智能极简园区' in n:
        return "智能极简园区网络配置命令，用于远端模块管理、备份组、端口扩展等。"
    
    # === 系统监控 ===
    if 'grpc' in n:
        return "gRPC配置命令，用于gRPC网管协议的配置。"
    if 'iflow' in n:
        return "iFlow配置命令，用于智能流量分析功能的配置。"
    if 'native-ip ifit' in n:
        return "Native-IP IFIT配置命令，用于随流检测功能配置。"
    if 'netstream' in n:
        return "NetStream配置命令，用于网络流量统计和分析。"
    if 'nqa' in n:
        return "NQA（网络质量分析）配置命令，用于网络性能测试和链路质量监控。"
    if 'packet event' in n:
        return "Packet Event配置命令，用于报文事件功能。"
    if 'pads' in n:
        return "PADS（主动防御系统）配置命令。"
    if 'ping' in n or 'tracert' in n:
        return "Ping和Tracert配置命令，用于网络连通性测试和路径追踪。"
    if 'said' in n:
        return "SAID配置命令，用于智能故障诊断功能。"
    if 'sflow' in n:
        return "sFlow配置命令，用于基于采样的网络流量监控。"
    if 'telemetry' in n:
        return "Telemetry配置命令，用于遥测数据订阅和上报。"
    if '报文捕获' in n:
        return "报文捕获配置命令，用于硬件转发和上送CPU报文的捕获功能。"
    if '故障策略中心' in n:
        return "故障策略中心（EVA）配置命令，用于智能故障管理和自愈策略。"
    if '镜像' in n:
        return "镜像配置命令，用于端口镜像功能。"
    if '数据采集' in n:
        return "数据采集配置命令。"
    if '业务诊断' in n:
        return "业务诊断配置命令，用于业务层面的故障诊断功能。"
    
    # === AAA/NAC ===
    if 'aaa' in n:
        return "AAA配置命令，用于认证、授权和计费功能。"
    if 'nac' in n:
        return "NAC（网络准入控制）配置命令，用于802.1X、MAC认证和Portal认证的接入控制。"
    if '策略联动' in n:
        return "策略联动配置命令，用于认证控制设备与认证接入设备之间的策略联动。"
    if '防私接' in n:
        return "防私接配置命令，用于检测和防范用户私自接入的NAT/代理设备。"
    if '系统主密钥' in n:
        return "系统主密钥配置命令，用于设备主密钥的管理。"
    if '业务随行' in n:
        return "业务随行配置命令，用于Free Mobility功能。"
    if '终端识别' in n:
        return "终端识别配置命令，用于识别终端类型。"
    
    # === 虚拟化 ===
    if '堆叠' in n:
        return "堆叠配置命令，用于多台设备的堆叠（iStack/CSS）功能。"
    
    # === 工业网络 ===
    if 'profinet' in n:
        return "PROFINET配置命令，用于工业以太网PROFINET协议的配置。"
    if 'tsn' in n:
        return "TSN（时间敏感网络）配置命令，用于工业网络中确定性低时延通信的配置。"
    
    # === 网络切片 ===
    if '网络切片' in n:
        return "网络切片配置命令，用于5G承载网中的网络切片功能。"
    
    # === 默认 ===
    return f"{name}相关配置命令。"


def generate_readmes():
    """为所有 depth-3 文件夹生成 README.md"""
    count = 0
    for root, dirs, files in os.walk(base):
        depth = root.replace(base, '').count(os.sep)
        if depth == 3:
            folder_name = os.path.basename(root)
            txt_files = sorted([f for f in os.listdir(root) 
                               if f.endswith('.txt') and f != '_说明.txt'])
            
            commands = []
            for tf in txt_files:
                name = tf.replace('.txt', '')
                func = get_func_lines(os.path.join(root, tf))
                commands.append({'name': name, 'func': func[:150] if func else ''})
            
            desc = categorize_folder(folder_name, commands)
            
            lines = [f"# {folder_name}", "", desc, ""]
            if commands:
                lines.append(f"本目录包含 {len(commands)} 条命令：")
                lines.append("")
                for c in commands:
                    lines.append(f"- **{c['name']}** - {c['func']}")
            
            readme_path = os.path.join(root, 'README.md')
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            count += 1
    
    print(f"Generated {count} README.md files for depth-3 folders")

if __name__ == '__main__':
    generate_readmes()
