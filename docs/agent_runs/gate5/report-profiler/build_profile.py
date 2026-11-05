import json, re
e=json.load(open('work/report_extract.json')); m=json.load(open('work/matches.json'))
hits=json.load(open('work/jurisdiction.json'))
B=e['blocks']
# explicit choices for ambiguous tokens: idx -> (name, context, reason)
R_BASE="base-case result stated in base-case text or table; equal display in a scenario is coincidental"
C={}
def s(i,n,c,r): C[i]=(n,c,r)
s(1,'dr_costs','base',"single rate stated for costs and outcomes; cost discount rate chosen as the representative input (outcome rate has the same value)")
for i,n,c in [(2,'res_int_total_cost','base'),(3,'res_int_qaly_disc','base'),(4,'res_comp_total_cost','base'),(5,'res_comp_qaly_disc','base'),(6,'res_inc_total_cost','base'),(7,'res_inc_qaly_disc','base'),(8,'res_icer','base'),(10,'res_inc_nmb','base')]:
    s(i,n,c,R_BASE)
s(9,'wtp_threshold','base',"upper end of the decision-maker threshold range, not a subsequent-therapy cost")
for i in (12,13):
    s(i,'int_admin_interval_weeks','base',"dosing interval in weeks of Drug A")
s(14,'comp_admin_interval_weeks','base',"dosing interval in weeks of Drug B")
s(15,'cycle_length_days','base',"cycle length in days")
s(18,'prop_male','base',"proportion of the cohort that is male")
s(20,'dr_costs','base',"first of the paired rates, for costs")
s(21,'dr_outcomes','base',"second of the paired rates, for outcomes")
s(22,'int_pfs_shape','base',"Weibull table, Drug A PFS row, shape column")
s(23,'int_pfs_scale','base',"Weibull table, Drug A PFS row, scale column")
s(24,'res_int_median_pfs','base',"Weibull table, Drug A PFS row, median column")
s(28,'int_tot_shape','base',"Weibull table, Drug A ToT row, shape column")
s(31,'comp_pfs_shape','base',"Weibull table, Drug B PFS row, shape column")
s(32,'comp_pfs_scale','base',"Weibull table, Drug B PFS row, scale column")
s(35,'comp_os_scale','base',"Weibull table, Drug B OS row, scale column")
s(42,'res_int_median_pfs','base',"median PFS of Drug A in survival text")
s(44,'int_admin_interval_weeks','base',"Drug A dosing interval in weeks")
s(46,'comp_admin_interval_weeks','base',"Drug B dosing interval in weeks")
s(49,'res_int_expected_vials','base',"expected vials per administration of Drug A; reported output cell preferred over its calculation twin")
s(51,'weight_sd_kg','base',"standard deviation of body weight in kg")
s(53,'res_comp_expected_vials','base',"vials per administration of Drug B flat dose; reported output cell")
s(54,'int_rdi','base',"relative dose intensity of Drug A")
s(55,'comp_rdi','base',"relative dose intensity of Drug B")
s(60,'res_int_drug_cost_per_admin','base',"cost inputs table, Drug A drug cost per administration; reported output cell")
s(61,'comp_vial_price','base',"cost inputs table, Drug B price per vial")
s(62,'res_comp_drug_cost_per_admin','base',"cost inputs table, Drug B drug cost per administration; reported output cell")
s(63,'int_admin_cost_per_admin','base',"cost inputs table, administration cost row for Drug A")
s(64,'comp_admin_cost_per_admin','base',"cost inputs table, administration cost row for Drug B")
s(68,'int_ae_cost','base',"cost inputs table, adverse event input for Drug A")
s(69,'comp_ae_cost','base',"cost inputs table, adverse event input for Drug B")
s(75,'st_cost_2','base',"subsequent therapy table, immunotherapy course cost")
s(81,'res_int_st_cost_per_progression','base',"subsequent therapy table, cost per progression after Drug A; reported output cell")
s(82,'res_comp_st_cost_per_progression','base',"subsequent therapy table, cost per progression after Drug B; reported output cell")
s(84,'u_pd','base',"utility table, progressed disease row")
s(86,'comp_ae_qaly_loss','base',"utility table, AE QALY loss for Drug B")
s(87,'gpu_intercept','base',"utility table, population norm intercept")
for i,n in [(91,'res_inc_ly_disc'),(92,'res_inc_qaly_disc'),(93,'res_inc_total_cost'),(94,'res_icer'),(95,'res_icer_ly'),
            (96,'res_int_total_cost'),(97,'res_comp_total_cost'),(98,'res_inc_total_cost'),
            (99,'res_int_ly_disc'),(100,'res_comp_ly_disc'),(101,'res_inc_ly_disc'),
            (102,'res_int_qaly_disc'),(103,'res_comp_qaly_disc'),(104,'res_inc_qaly_disc'),(105,'res_icer'),(106,'res_inc_nmb')]:
    s(i,n,'base',R_BASE)
s(107,'res_int_ly_undisc','base',"undiscounted life years of Drug A, base case")
s(108,'res_comp_ly_undisc','base',"undiscounted life years of Drug B, base case; not an incremental value")
s(109,'res_int_drug_share','base',"drug acquisition share of Drug A total costs, base case")
s(110,'res_comp_drug_share','base',"drug acquisition share of Drug B total costs, base case")
for i,n in [(118,'res_int_cost_pf_state'),(120,'res_inc_cost_pf_state'),(121,'res_int_cost_pd_state'),(122,'res_comp_cost_pd_state'),
            (123,'res_inc_cost_pd_state'),(124,'res_int_cost_terminal'),(125,'res_comp_cost_terminal'),(126,'res_inc_cost_terminal'),
            (127,'res_int_cost_st'),(129,'res_inc_cost_st'),(133,'res_int_total_cost'),(134,'res_comp_total_cost'),(135,'res_inc_total_cost')]:
    s(i,n,'base',"disaggregated base-case cost table, row and arm column")
s(130,'res_int_cost_ae','base',"disaggregated cost table, adverse events, Drug A column; result output rather than the input cell")
s(131,'res_comp_cost_ae','base',"disaggregated cost table, adverse events, Drug B column; result output rather than the input cell")
s(136,'res_inc_total_cost','base',"scenario table, base case row")
s(137,'res_inc_qaly_disc','base',"scenario table, base case row")
s(138,'res_icer','base',"scenario table, base case row")
s(139,'dr_costs','SC1',"scenario table, lower discount rate row, setting column displays the cost rate")
s(149,'res_inc_total_cost','base',"alternative utility scenario row; utilities do not change costs, so the value is the base-case cell (scenario context not offered as a candidate)")
s(154,'res_inc_qaly_disc','base',"no stopping rule scenario row; dosing does not change QALYs, so the value is the base-case cell (scenario context not offered as a candidate)")
s(160,'res_inc_total_cost','SC6',"scenario table, no general-population mortality constraint row")
s(161,'res_inc_qaly_disc','SC6',"scenario table, no general-population mortality constraint row")
s(162,'res_icer','SC6',"scenario table, no general-population mortality constraint row")
s(163,'res_inc_total_cost','base',"no utility age adjustment scenario row; utilities do not change costs, so the value is the base-case cell (scenario context not offered as a candidate)")
s(166,'int_tot_shape','SC8',"scenario table, ToT equal to PFS row, shape setting")
s(167,'int_tot_scale','SC8',"scenario table, ToT equal to PFS row, scale setting")
s(169,'res_inc_qaly_disc','base',"ToT equal to PFS scenario row; treatment duration does not change QALYs, so the value is the base-case cell (scenario context not offered as a candidate)")
s(171,'wtp_threshold','base',"upper threshold against which scenario ICERs are compared")
s(178,'res_int_gpm_first_bind_age','base',"age at which the mortality constraint first binds, not a price")
s(180,'res_icer','base',"base-case ICER in conclusion")
s(181,'wtp_threshold','base',"decision threshold")
s(183,'wtp_threshold','base',"upper end of the threshold range")

nums=[];unres=[]
for i,(t,c) in enumerate(zip(e['tokens'],m)):
    assert t['token']==c['token'] and t['block']==c['block']
    cands={(x['name'],x['context']) for x in c['candidates']}
    if i in C:
        n,ctx,r=C[i]
    elif c['status']=='unique':
        x=c['candidates'][0]; n,ctx=x['name'],x['context']; r="single candidate, consistent with the surrounding text"
    else:
        n,ctx,r=None,None,None
    if n is None or (n,ctx) not in cands:
        raise SystemExit(f"no valid choice for T{i}: {n}@{ctx}")
    assert not re.search(r'\d', r), (i,r)
    nums.append({"token_index":i,"block":t['block'],"token":t['token'],"name":n,"context":ctx,"reason":r})
# sections
secs=[];cur=None
for b in B:
    if b['kind']=='heading':
        txt=b['text']
        if re.match(r'^\d+\.\d+\s',txt) and cur is not None:
            cur['children'].append({"heading":txt,"block":b['index']})
        else:
            cur={"heading":txt,"block":b['index'],"children":[]}; secs.append(cur)
json.dump({"numerals":nums,"unresolved":unres,"sections":secs,"jurisdiction_hits":hits},open('work/report_profile.json','w'),indent=1)
