<macro>
def to_bool(captured_data):
    represent_as_bools = ["preempt", "Port-Channel" ]
    if captured_data in represent_as_bools:
      return captured_data, {captured_data: True}
</macro>
<group name="interfaces.{{interface}}">
interface {{ interface | _start_ }}
 switchport mode {{ mode }}
 switchport trunk allowed vlan {{ vlans_allowed | unrange(rangechar='-', joinchar=',' ) | split(',') }}
 switchport access vlan {{ vlan }}
 speed {{speed}}
 duplex {{duplex}}
 description {{ description | ORPHRASE }}
 encapsulation dot1q {{ dot1q }}
 ip address {{ ip }} {{ mask }}
 ip vrf {{ vrf }}
 vrf forwarding {{ vrf }}
 shutdown {{ shutdown | set(True) }}
 negotiation {{ negation }}
 ip directed-broadcast {{ ip_directed_broadcast | set(True) }}
 mac access-group {{ input_mac_acl }} in
 mac access-group {{ output_mac_acl }} out
 service-policy input {{ input_policy }}
 service-policy output {{ output_policy }}
 <group name="service_instance.{{id}}">
 {{ pop | set(None) }}
 {{ symmetric | set(False) }}
 {{ input_policy | set(None) }}
 {{ output_policy | set(None) }}
 service instance {{ id | record(id) | _start_ }} ethernet
  description {{ description }}
  <group name="encapsulation">
  {{ second_vlan | set(None) }}
  {{ vlan | set(None) }}
  encapsulation dot1q {{ vlan | _start_ }} second-dot1q {{ second_vlan }}
  encapsulation {{ vlan | _start_ }}
  encapsulation dot1q {{ vlan | _start_ }}
  </group>
  rewrite ingress tag pop {{ pop }} {{ symmetric }}
  service-policy input {{ input_policy }}
  service-policy output {{ output_policy }}
  bridge-domain {{ bdomain }}
  <group name="xconnect">
  {{ neighbor | set(None) }}
  {{ vc_id | set(None) }}
  {{ mtu | set(None) }}
  xconnect {{ neighbor }} {{ vc_id }} encapsulation mpls
   mtu {{ mtu }}
  </group>
 </group>

 channel-group {{ channel_group | DIGIT }} mode {{ channel_mode }}

 <group name="hsrp.{{ standbygroup }}">
 standby version {{ version | record(version) }}
 standby {{ standbygroup | DIGIT }} ip {{ ip | _start_ }}
 standby {{ standbygroup | DIGIT }} priority {{ priority }}
 standby {{ standbygroup | DIGIT }} authentication {{ authentication }}
 standby {{ standbygroup | DIGIT }} {{ preempt | macro("to_bool") }}
 {{ version | set(version)}}
 {{ additional_hsrp_cfg | _line_ | contains("standby ") | joinmatches }}
 </group>

!{{ _end_ }}
</group>

<group name="global.service">
{{ service | _line_ | contains("service ") | joinmatches }}
!{{ _end_ }}
</group>

<group name="global.fqdn">
hostname {{ hostname | ORPHRASE }}
ip domain name {{ domain_name }}
</group>

<group name="global.vlan.{{vid}}">
vlan {{ vid | _start_ }} 
 name {{ name }}
 mtu {{ mtu }}
## vlan {{ id | _start_ | unrange(rangechar='-', joinchar=',' ) | split(',') }}
!{{ _end_ }}
</group>

<group name="global.vtp">
{{ enabled | set(True) }}
vtp mode transparent{{ enabled | set(False) }}
</group>

<group name="global.http_server">
no ip http server{{ http_server | set(False) }}
ip http server{{ http_server | set(True) }}
no ip http secure-server{{ http_secure_server | set(False) }}
ip http secure-server{{ http_secure_server | set(True) }}
</group>

<group name="global.version">
version {{ version  | ORPHRASE }}
</group>

<group name="routing.routes">
{{ weight | set(None) }}
ip route {{src | _start_}} {{mask}} {{dest}} {{weight}}
ip route {{src | _start_}} {{mask}} {{dest}}
</group>

<group name="management.lldp_run">
{{ enabled | set(False) }}
lldp run{{ enabled | set(True) }}
</group>

<group name="management.cdp_run">
{{ enabled | set(True) }}
no cdp run{{ enabled | set(False) }}
</group>

<group name="management.scp_server">
</group>

<group name="management.ssh">
{{ scp | set(False) }}
ip ssh version {{ version }}
ip scp server enable {{ scp | set(True) }}
</group>

<group name="management.enable">
{{ secret | set(None) }}
{{ password | set(None) }}
enable secret 9 {{ secret }}
enable password {{ password }}
</group>

<group name="management.snmp">
<group name="access" method="table">
snmp-server group {{ group}} {{version}} auth {{ auth | re("read|write|context") }} {{access_list}}
snmp-server group {{ group}} {{version}} auth {{ auth | re("read|write|context") }} {{write_view}} access {{access_list}}
snmp-server group {{ group}} {{version}} auth context {{context}} match {{match}} access {{access_list}}
snmp-server community {{community}} {{mode}}
</group>
<group name="various">
snmp-server view {{ view_name | _start_ }} {{view_mib_family}} {{ inc_exc | re("(include|exclude)") }}
snmp-server location {{ snmp_location | re(".*") | _start_ | joinmatches(',') }}
snmp-server contact {{ contact | _start_ | joinmatches(',') }}
snmp-server host {{trap_host | _start_ | joinmatches(',') }} {{community}}
snmp-server trap-source {{trap_source | _start_ | joinmatches(',') }}
</group>
<group name="enabled_traps.{{ traps_name }}">
snmp-server enable traps {{ traps_name | ORPHRASE | _start_ }}
</group>
snmp-server host {{trap_host | _start_ }} version 2c {{community}}
</group>

<group name="management.logging">
logging facility {{facility}}
logging source-interface {{source_interface}}
<group name="hosts">
logging host {{host}}
</group>
</group>

<group name="management.ntp">
ntp server {{ ip_address }}
</group>

<group name="management.line.{{vty}}">
line {{ vty | ORPHRASE | record(vty) }}
 {{ password | set(None) }}
 logging {{logging}}
 stopbits {{stopbits}}
 login {{ local }}
 length {{ value }}
 transport input {{ input }}
 transport output {{ output }}
 session-timeout {{ timeout }}
 password {{ password }}
</group>

<group name="management.archive">
archive
 path {{ path }}
 write {{ write }}
</group>

<group name="global.redundancy">
redundancy
 mode {{ mode }}
</group>

<group name="routing.vrf">
vrf {{ vrf | ORPHRASE | record(vrf) }}
 definition {{vrf_name}}
 address-family {{af}}
 exit-address-family
</group>

<group name="routing.ospf.{{process}}">
router ospf {{ process | ORPHRASE | record(process) }}
 {{ router_id | set(None) }}
 router-id {{ router_id }}
 <group name="area.{{area}}">
 area {{ area }} {{ area_type }}
 </group>
 {{ passive_interface_enabled | set(False) }}
 passive-interface default {{ passive_interface_enabled | set(True) }}
<group name="no_passive_interface">
 no passive-interface {{interface}}
</group>
<group name="networks.{{network}}" record="network">
 network {{network | PHRASE | to_ip | with_prefixlen}} area {{area}}
</group>
</group>

<group name="routing.rip">
router rip
 version {{version}}
 redistribute {{redistribute}}
 <group name="address_family.{{afi}}.{{vrf}}">
 address-family {{afi}} vrf {{vrf}}
  <group name="redistribute.{{redistribute}}">
  redistribute {{redistribute}}
  </group>
  <group name="networks.{{network}}">
  network {{network}}
  </group>
  {{ auto_summary_disabled | set(False) }}
  no auto-summary{{ auto_summary_disabled | set(True) }}
  version {{version}}
 exit-address-family
</group>
!{{ _end_ }}
</group>

<group name="routing.eigrp">
router eigrp {{as_number}}
 {{ passive_interface_enabled | set(False) }}
 passive-interface default {{ passive_interface_enabled | set(True) }}
<group name="no_passive_interface">
 no passive-interface {{interface}}
</group>
<group name="network">
 network {{network | _start_ }} {{wildcard}}
 network {{network | _start_ }}
</group>
{{ auto_summary_enabled | set(True) }}
 no auto-summary{{ auto_summary_enabled | set(False) }}
</group>

<group name="routing.bgp">
router bgp {{ asn | record(asn) }}
 neighbor {{ neighbor_ip }} remote-as {{ remote_as }}
 neighbor {{ neighbor_ip }} update-source {{ update_source }}
  {{ auto_summary_enabled | set(True) }}
  no auto-summary{{ auto_summary_enabled | set(False) }}
  <group name="vrfs.{{ vrf_name }}" record="vrf_name">
 vrf {{ vrf_name }}
  <group name="peers" chain="chain_1">
  neighbor {{ peer_ip }}
   {{ local_asn | set(asn) }}
   {{ hostname | set(hostname) }}
   remote-as {{ remote_as }}
   description {{ description }}
   address-family {{ afi }} unicast
    route-map {{ rpl_in }} in
    route-map {{ rpl_out }} out
	 </group>
  </group>
</group>

<group name="security.access_list.standard.{{access_list_id}}" method="table">
access-list {{access_list_id}} remark {{remark}}
access-list {{access_list_id}} {{rule | re("permit|deny") }} {{host}}
access-list {{access_list_id}} {{rule | re("permit|deny") }} {{host}} {{log}}
</group>

<group name="security.access_list.standard.{{access_list_id}}">
ip access-list standard {{access_list_id | _start_ }}
<group name="rules" method="table">
 {{action | re("permit|deny") }} {{ host | IP }}
 {{action | re("permit|deny") }} {{ host | IP }} {{log | _exact_ | set(True)}}
 {{action | re("permit|deny") }} {{ host | IP }} {{wildcard | IP }}
 {{action | re("permit|deny") }} {{ host | IP }} {{wildcard | IP }} {{log | _exact_ | set(True)}}
</group>
</group>

<group name="security.access_list.extended.{{access_list_id}}">
ip access-list extended {{access_list_id | _start_ }}
<group name="rules" method="table">
 {{ID | digit }} remark {{ remark | ORPHRASE}}
 {{ID | digit }} {{action | re("permit|deny") }} {{ protocol | WORD }} {{ src | IP }} {{ wildcard | IP }} {{ dest | WORD }} eq {{ service | ORPHRASE }}
 {{ID | digit }} {{action | re("permit|deny") }} {{ protocol | WORD }} {{ src | WORD }} {{ dst | WORD }} {{ rest | _line_ }}
</group>
</group>

<group name="security.aaa">
aaa new-model
aaa {{mode}} {{aaa}} default group {{primary}} {{secondary}}
</group>

<group name="security.radius">
radius-server host {{host}} auth-port {{auth_port}} acct-port {{acct_port}} key {{key}}
</group>

<group name="security.tacacs">
tacacs-server host {{host}} key 7 {{key}}
</group>

<group name="security.local_user">
username {{username}} privilege {{priv}} secret {{secret_type}} {{secret}}
</group>

<group name="global.policy.policy">
policy-map {{ policy_map | ORPHRASE | record(vrf) }}
<group name="class.{{ class_name }}">
 class {{ class_name }}
  bandwidth remaining percent {{ bandwith_remaining_percent | _start_ }}
  set dscp {{ set_dscp | _start_ }}
  set cos {{ set_cos | _start_ }}
  set qos-group {{ set_qos_group | _start_ }}
</group>
</group>

<group name="global.policy.class">
class-map match-{{match_type}} {{class_name}}
 <group name="match">
 match {{type}} name {{ name | ORPHRASE }}
## match {{type}} {{ value | ORPHRASE | unrange(rangechar='-', joinchar='  ' ) | split('  ') }}
</group>
</group>

<group name="global.bridge_domain.{{name}}">
bridge-domain {{name}}
{{ igmp_snooping_enabled | set(True) }}
 no ip igmp snooping{{ igmp_snooping_enabled | set(False) }}
</group>
