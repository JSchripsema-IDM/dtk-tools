import itertools
from dtk.vector.study_sites import configure_site
from dtk.tools.calibration.calibtool.geography_calibration import set_geography as set_geography_calibration

class Builder(object):
    '''
    Classes derived from Builder have generators that
    yield ModList(fn1(cb),fn2(cb),...) 
    where each function (fn) modifies the base ConfigBuilder (cb)
    and builds up metadata that is reset on ModList init
    '''
    metadata={}

    class ModList(list):
        def __init__(self, *args):
            Builder.metadata={}
            list.__init__(self, args)

    def __init__(self, mod_generator):
        self.mod_generator=mod_generator

    @classmethod
    def param_fn(cls,k,v):
        def fn(cb):
            cls.metadata.update({k:v})
            return cb.set_param(k,v)
        return fn

    @classmethod
    def site_fn(cls,s):
        def fn(cb):
            cls.metadata.update({'_site_':s})
            return configure_site(cb,s)
        return fn

    @classmethod
    def calib_site_fn(cls,s):
        def fn(cb):
            cls.metadata.update({'_site_':s})
            return set_geography_calibration(cb, s)
        return fn

    @classmethod
    def drug_param_changes_fn(cls,drugname,p,v):
        def fn(cb):
            cls.metadata.update({drugname+'_'+p:v})
            return cb.config['parameters']['Malaria_Drug_Params'][drugname].update({p:v})
        return fn

    @classmethod
    def vector_species_param_changes_fn(cls,vector,p,v):
        def fn(cb):
            cls.metadata.update({vector+'_'+p:v})
            return cb.config['parameters']['Vector_Species_Params'][vector].update({p:v})
        return fn

    @classmethod
    def set(cls,pv_pairs):
        m=cls.ModList()
        if '_site_' in dict(pv_pairs) : # do site first so that configure_sites won't overwrite other sweep parameters
            m.append(cls.site_fn(dict(pv_pairs)['_site_']))
        if '_calibsite_' in dict(pv_pairs) : # do site first so that configure_sites won't overwrite other sweep parameters
            m.append(cls.calib_site_fn(dict(pv_pairs)['_calibsite_']))
        for (p,v) in pv_pairs:
            if p=='_site_' or p=='_calibsite_':
                continue
            elif p.split('_')[0] == 'AntiMalDrug' : # to sweep over a drug parameter, use 'Drug_DRUGNAME_PARAMNAME' as parameter name in script file
                drugname = p.split('_')[1]
                drugp = '_'.join(p.split('_')[2:])
                m.append(cls.drug_param_changes_fn(drugname,drugp,v)) 
            elif p.split('_')[0] == 'VectorSpec' : # to sweep over a vector species parameter, use 'Vector_VECTORNAME_PARAMNAME' as parameter name in script file
                vector = p.split('_')[1]
                vecp = '_'.join(p.split('_')[2:])
                m.append(cls.vector_species_param_changes_fn(vector,vecp,v))
            elif p and p[0]=='_':
                raise NotImplementedError('Future general function, e.g. add_event')
            else:
                m.append(cls.param_fn(p,v))
        return m

class DefaultSweepBuilder(Builder):
    def __init__(self):
        self.mod_generator = (self.set([]) for _ in range(1))

class RunNumberSweepBuilder(Builder):
    def __init__(self,nsims):
        self.mod_generator = (self.set([('Run_Number',i)]) for i in range(nsims))

class GenericSweepBuilder(Builder):
    @classmethod
    def from_dict(cls, d):
        params=d.keys()
        combos=itertools.product(*d.values())
        return cls((cls.set(zip(params,combo)) for combo in combos))

    @classmethod
    def from_list(cls, p, v) :
        return cls((cls.set(zip(p,combo)) for combo in v))