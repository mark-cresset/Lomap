#############################################################################
# Lomap2: A toolkit to plan alchemical relative binding affinity calculations
# Copyright 2015 - 2016  UC Irvine and the Authors
#
# Authors: Dr Gaetano Calabro' and Dr David Mobley
# 
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, see http://www.gnu.org/licenses/
#############################################################################

from rdkit import Chem
from rdkit.Chem import rdFMCS
from rdkit.Chem import AllChem
from rdkit.Chem.Draw.MolDrawing import DrawingOptions
from rdkit.Chem import Draw
from optparse import OptionParser
import sys
import math



class MCS(object):
    """
    This class is used to compute the Maximum Common Subgraph (MCS) between two
    RDkit molecule objects.  
    
    """

    def __init__(self, moli, molj, options):
        """
        Inizialization function
    
        moli: Rdkit molecule object related to the first molecule used to 
        perform the MCS calculation
        molj: Rdkit molecule object related to the second molecule used to 
        perform the MCS calculation
        options: MCS options

        """

        def map_mcs_mol():
            """
            This function is used to define a map between the generated mcs, the
            starting molecules and vice versa
    
            mcs_mol: the mcs molecule generated from the mcs calulation between 
            the two passed molecules
 
            """
   
            # mcs indexes mapped back to the first molecule moli
            moli_sub = self.__moli_noh.GetSubstructMatch(self.mcs_mol)
              
            mcsi_sub = self.mcs_mol.GetSubstructMatch(self.mcs_mol)
            
            # mcs to moli
            map_mcs_mol_to_moli_sub = zip(mcsi_sub, moli_sub)

            #print  map_mcs_mol_to_moli_sub
           
            # An RDkit atomic property is defined to store the mapping to moli
            for idx in map_mcs_mol_to_moli_sub:
                self.mcs_mol.GetAtomWithIdx(idx[0]).SetProp('to_moli', str(idx[1]))

            # mcs indexes mapped back to the second molecule molj 
            molj_sub = self.__molj_noh.GetSubstructMatch(self.mcs_mol)
              
            mcsj_sub = self.mcs_mol.GetSubstructMatch(self.mcs_mol)
             
            # mcs to molj
            map_mcs_mol_to_molj_sub = zip(mcsj_sub, molj_sub)
             
            #print map_mcs_mol_to_molj_sub
            
            #Map between the two molecules
            self.__map_moli_molj = zip( moli_sub, molj_sub)

            # An RDkit atomic property is defined to store the mapping to molj
            for idx in map_mcs_mol_to_molj_sub:
                self.mcs_mol.GetAtomWithIdx(idx[0]).SetProp('to_molj', str(idx[1]))

            # Chirality
            chiral_at_moli_noh = [seq[0] for seq in Chem.FindMolChiralCenters(self.__moli_noh)]
            chiral_at_molj_noh = [seq[0] for seq in Chem.FindMolChiralCenters(self.__molj_noh)]

            chiral_at_mcs_moli_noh = set([seq[0] for seq in map_mcs_mol_to_moli_sub if seq[1] in chiral_at_moli_noh])
            chiral_at_mcs_molj_noh = set([seq[0] for seq in map_mcs_mol_to_molj_sub if seq[1] in chiral_at_molj_noh])

            chiral_at_mcs = chiral_at_mcs_moli_noh | chiral_at_mcs_molj_noh
            
            for i in chiral_at_mcs:
                at = self.mcs_mol.GetAtomWithIdx(i)
                at.SetChiralTag(Chem.rdchem.ChiralType.CHI_TETRAHEDRAL_CW)


            if chiral_at_mcs:
                print('Chiral atoms detected')

            #For each mcs atom we save its original index in a specified 
            #property. This could be very usefull in the code development
            for at in self.mcs_mol.GetAtoms():
                at.SetProp('org_idx',str(at.GetIdx()))


            return


        def set_ring_counter(mol):
            
            for at in mol.GetAtoms():
                at.SetProp('rc','0')

            rginfo = mol.GetRingInfo()

            rgs = rginfo.AtomRings()
         
            #print rgs
   
            rgs_set = set([e for l in rgs for e in l])
            
            for idx in rgs_set:
                for r in rgs:
                    if(idx in r):
                        val = int(mol.GetAtomWithIdx(idx).GetProp('rc'))
                        val = val + 1
                        mol.GetAtomWithIdx(idx).SetProp('rc',str(val))
            return
            

        # Local pointers to the passed molecules
        self.moli = moli
        self.molj = molj

        # Local pointers to the passed molecules without hydrogens
        # These variables are defined as private
        self.__moli_noh = AllChem.RemoveHs(moli)
        self.__molj_noh = AllChem.RemoveHs(molj)
        

        # MCS pattern calculation
        self.__mcs = rdFMCS.FindMCS([self.__moli_noh, self.__molj_noh],
                                          timeout=options.time, 
                                          atomCompare=rdFMCS.AtomCompare.CompareAny, 
                                          bondCompare=rdFMCS.BondCompare.CompareAny, 
                                          matchValences=False, 
                                          ringMatchesRingOnly=True, 
                                          completeRingsOnly=False, 
                                          matchChiralTag=False)
        
        # Checking
        if self.__mcs.canceled:
            print 'Timeout reached to find the MCS between molecules: %d and %d' \
            % (self.moli.getID(),self.molj.getID())          
        if self.__mcs.numAtoms == 0:
            print 'No MCS was found between molecules: %d and %d' \
            % (self.moli.getName(),self.molj.getName())
            raise ValueError()
            
        # The found MCS pattern (smart strings) is converted to a RDkit molecule
        self.mcs_mol = Chem.MolFromSmarts(self.__mcs.smartsString)

        
        try:#Sanitize the MCS molecule
            with suppress_stdout_stderr():
                Chem.SanitizeMol(self.mcs_mol)

        except:    
            sanitFail = Chem.SanitizeMol(self.mcs_mol, sanitizeOps=Chem.SanitizeFlags.SANITIZE_SETAROMATICITY, catchErrors=True)
            if sanitFail:
                print 'Sanitization Failed...'
                raise ValueError(sanitFail)

        # Mapping between the found MCS molecule and moli,  molj
        map_mcs_mol()

        #Set the ring counters for each molecule
        set_ring_counter(self.__moli_noh)
        set_ring_counter(self.__molj_noh)
        set_ring_counter(self.mcs_mol)

        
        # for at in self.mcs_mol.GetAtoms():
        #     print 'at = %d rc = %d' % (at.GetIdx(), int(at.GetProp('rc')))


        return

    def getMap(self):
        """
        This function is used to return a list of the atom index pair generated
        from themapping between the two molecules used to calculate the MCS.
        """
        return self.__map_moli_molj


    def draw_molecule(self,mol,fname='mol.png'):
        
        DrawingOptions.includeAtomNumbers=True
        AllChem.Compute2DCoords(mol)
        Chem.Draw.MolToFile(mol,fname)
        
        for at in mol.GetAtoms():
            print 'atn = %d rc = %d org = %d to_molij = (%d,%d)' \
                % (at.GetIdx(), int(at.GetProp('rc')),  
                   int(at.GetProp('org_idx')),
                   int(at.GetProp('to_moli')), int(at.GetProp('to_molj')))
        return
        


    def draw_mcs(self, fname = 'mcs.png'):
        """
        This function is used to draw the passed molecules and their mcs molecule
        At this stage it is used as debugging tools
                    
        """
   
        #Copy of the molecules
        moli_noh = Chem.Mol(self.__moli_noh)
        molj_noh = Chem.Mol(self.__molj_noh)
        mcs_mol = Chem.Mol(self.mcs_mol) 
        

        try:
            Chem.SanitizeMol(self.mcs_mol)
        except ValueError:
            print('Sanitization failed....')
        

        moli_sub = moli_noh.GetSubstructMatch(self.mcs_mol)
        molj_sub = molj_noh.GetSubstructMatch(self.mcs_mol)

        mcs_sub =  self.mcs_mol.GetSubstructMatch(self.mcs_mol)
        
        AllChem.Compute2DCoords(moli_noh)
        AllChem.Compute2DCoords(molj_noh)
        AllChem.Compute2DCoords(self.mcs_mol)
               
        DrawingOptions.includeAtomNumbers=True
        
        moli_fname='Moli'
        molj_fname='Molj'
        mcs_fname = 'Mcs'

        img = Draw.MolsToGridImage([moli_noh, molj_noh, self.mcs_mol], 
                                   molsPerRow=3, subImgSize=(400,400),
                                   legends=[moli_fname,molj_fname,mcs_fname], 
                                   highlightAtomLists=[moli_sub, molj_sub, mcs_sub] )

        img.save(fname)

        
        return

    ############ RULES ############

    #ECR Rule (Electrostatic rule)
    def ecr(self):
         
        total_charge_moli = 0.0
            
        for atom in self.moli.GetAtoms():
            total_charge_moli += float(atom.GetProp('_TriposPartialCharge'))

        total_charge_molj = 0.0
        for atom in self.molj.GetAtoms():
            total_charge_molj += float(atom.GetProp('_TriposPartialCharge'))

        if abs(total_charge_molj - total_charge_moli) < 1e-3:
            scr_ecr = 1.0
        else:
            scr_ecr = 0.0

            
        return scr_ecr


    # MCSR Rule
    def mcsr(self, beta=0.1):
        
        # number heavy atoms
        nha_moli = self.moli.GetNumHeavyAtoms()
        nha_molj = self.molj.GetNumHeavyAtoms()
        nha_mcs_mol = self.mcs_mol.GetNumHeavyAtoms()
            
        scr_mcsr = math.exp(-beta*(nha_moli + nha_molj - 2*nha_mcs_mol))

        return scr_mcsr


    # MNACR rule
    def mncar(self, ths=4):
        
        #This rule has been modified from the rule desribed in the Lomap paper
        #to match the implemented version
 
        nha_mcs_mol = self.mcs_mol.GetNumHeavyAtoms()
        nha_moli = self.moli.GetNumHeavyAtoms()
        nha_molj = self.molj.GetNumHeavyAtoms()
    
        scr_mncar = float((nha_mcs_mol >= ths) or (nha_moli + 3) or (nha_molj + 3))
     
        return scr_mncar


    # TMCRS rule (Trim rule) 
    def tmcsr(self, beta=0.1, strict_flag=True):
        
        def delete_broken_ring():

            #Strict: we cancel all the atoms in conflict in the mcs and 
            #delete all eventually non ring atoms that are left 
            def extend_conflict(mol, conflict):
                
                mcs_conflict = list(conflict)
                mcs_conflict.sort(reverse=True)


                #Editing the mcs molecule deleting all the selected conficting atoms
                edit_mcs_mol = Chem.EditableMol(mol)

                #WARNING: atom indexes are changed
                for i in mcs_conflict:
                    edit_mcs_mol.RemoveAtom(i) 
                
                mcs_mol = edit_mcs_mol.GetMol()
              
                #The mcs molecule could be empty at this point
                if not mcs_mol.GetNumAtoms():
                    return mcs_mol
                
                #Deleting broken ring atoms if the atom rc > 0 and the atom is not 
                #in a ring anymore
                mcs_conflict = [ at.GetIdx()  for at in mcs_mol.GetAtoms() if int(at.GetProp('rc')) > 0 and not at.IsInRing()]
                
                mcs_conflict.sort(reverse=True)

                edit_mcs_mol = Chem.EditableMol(mcs_mol)
                
                #WARNING: atom indexes are changed
                for i in mcs_conflict:
                    edit_mcs_mol.RemoveAtom(i) 
                    
                mcs_mol = edit_mcs_mol.GetMol()

                #The mcs molecule could be empty at this point
                if not mcs_mol.GetNumAtoms():
                    return mcs_mol

                #Deleting eventually disconnected parts and keep the max fragment left
                fragments = Chem.rdmolops.GetMolFrags(mcs_mol)

                max_idx = 0
                lgt_max = 0
        
                for idx in range(0,len(fragments)):
                    lgt = len(fragments[idx])
                    if lgt > lgt_max:
                        lgt_max = lgt
                        max_idx = idx
    
                        
                max_frag = fragments[max_idx]

                mcs_conflict = [ at.GetIdx() for at in mcs_mol.GetAtoms() if not at.GetIdx() in max_frag ]
        
                mcs_conflict.sort(reverse=True)

                edit_mcs_mol = Chem.EditableMol(mcs_mol)

                #WARNING: atom indexes have changed
                for i in mcs_conflict:
                    edit_mcs_mol.RemoveAtom(i) 
                    
                mcs_mol = edit_mcs_mol.GetMol()

                #self.draw_molecule(mcs_mol)

                return mcs_mol
                
            
            mcs_conflict = set()
            
            for at in self.mcs_mol.GetAtoms():

                moli_idx = int(at.GetProp('to_moli'))
                molj_idx = int(at.GetProp('to_molj'))

                moli_idx_rc =  int(self.__moli_noh.GetAtomWithIdx(moli_idx).GetProp('rc'))
                molj_idx_rc =  int(self.__molj_noh.GetAtomWithIdx(molj_idx).GetProp('rc'))
                
                #Moli atom is a ring atom (rc>0) and its rc is different from 
                #the corresponding mcs rc atom  
                if moli_idx_rc > 0 and (moli_idx_rc != int(at.GetProp('rc'))):
                    if strict_flag:#In strict mode we add the atom
                        mcs_conflict.add(at.GetIdx())
                    else:#In loose mode we add the atom if it is a not aromatic atom only
                        if not at.GetIsAromatic():
                            mcs_conflict.add(at.GetIdx())
                        

                #Molj atom is a ring atom (rc>0) and its rc is different 
                #from the corresponding mcs rc atom 
                if molj_idx_rc > 0 and (molj_idx_rc  != int(at.GetProp('rc'))):
                    if strict_flag:#In strict mode we add the atom
                        mcs_conflict.add(at.GetIdx())
                    else:#In loose mode we add the atom if it is a not aromatic atom only
                        if not at.GetIsAromatic():
                            mcs_conflict.add(at.GetIdx())

            mcs_mol = extend_conflict(self.mcs_mol, mcs_conflict)
            
                        
            return mcs_mol


        mcs_mol_copy = Chem.Mol(self.mcs_mol)

        orig_nha_mcs_mol = mcs_mol_copy.GetNumHeavyAtoms() 


        #At this point the mcs_mol_copy has changed 
        mcs_mol_copy = delete_broken_ring()

        #The mcs molecule could be empty at this point
        if not mcs_mol_copy.GetNumAtoms():
            return math.exp(-2*beta*(orig_nha_mcs_mol))


        #Deleting Chiral Atoms
        mcs_ring_set = set()
        mcs_chiral_set = set()

        for atom in mcs_mol_copy.GetAtoms():
                if atom.IsInRing():
                    mcs_ring_set.add(atom.GetIdx())
                if atom.GetChiralTag() == Chem.rdchem.ChiralType.CHI_TETRAHEDRAL_CW:
                    mcs_chiral_set.add(atom.GetIdx())
        
        
        #Loop over the mcs chirial atoms to check if they are also ring atoms
        delete_atoms = set()
        
        for atom_idx in mcs_chiral_set:
            
            if atom_idx in mcs_ring_set:
                
                at = mcs_mol_copy.GetAtomWithIdx(atom_idx)
               
                neighs = at.GetNeighbors()
                neighs_set = set()

                for atom in neighs:
                    neighs_set.add(atom.GetIdx())
        
                delete_atoms |= (neighs_set - mcs_ring_set)

            else:
                #If the chiral atom is not a ring atom, we delete it
                delete_atoms.add(atom_idx)


        delete_atoms = list(delete_atoms)

        delete_atoms.sort(reverse=True)
    
        edit_mcs_mol = Chem.EditableMol(mcs_mol_copy)

        #WARNING atom indexes have changed
        for idx in delete_atoms:
            edit_mcs_mol.RemoveAtom(idx)

        mcs_mol_copy = edit_mcs_mol.GetMol()

        
        #The mcs molecule could be empty at this point
        if not mcs_mol_copy.GetNumAtoms():
            return math.exp(-2*beta*(orig_nha_mcs_mol))


        #self.draw_molecule(mcs_mol_copy)

        fragments = Chem.rdmolops.GetMolFrags(mcs_mol_copy)

        max_idx = 0
        lgt_max = 0
        
        for idx in range(0,len(fragments)):
            lgt = len(fragments[idx])
            if lgt > lgt_max:
                lgt_max = lgt
                max_idx = idx
    
            
        max_frag = fragments[max_idx]
        
        #The number of heavy atoms in the max fragment
        max_frag_num_heavy_atoms = 0
        for idx in max_frag:
            at = mcs_mol_copy.GetAtomWithIdx(idx)
            if at.GetAtomicNum() > 1:
                max_frag_num_heavy_atoms += 1   


        return math.exp(-2*beta*(orig_nha_mcs_mol - max_frag_num_heavy_atoms))
        


class suppress_stdout_stderr(object):
    '''
    This function has been pasted form intenret
    A context manager for doing a "deep suppression" of stdout and stderr in 
    Python, i.e. will suppress all print, even if the print originates in a 
    compiled C/Fortran sub-function.
       This will not suppress raised exceptions, since exceptions are printed
    to stderr just before a script exits, and after the context manager has
    exited (at least, I think that is why it lets exceptions through).      

    '''
    def __init__(self):
        # Open a pair of null files
        self.null_fds =  [os.open(os.devnull,os.O_RDWR) for x in range(2)]
        # Save the actual stdout (1) and stderr (2) file descriptors.
        self.save_fds = (os.dup(1), os.dup(2))

    def __enter__(self):
        # Assign the null pointers to stdout and stderr.
        os.dup2(self.null_fds[0],1)
        os.dup2(self.null_fds[1],2)

    def __exit__(self, *_):
        # Re-assign the real stdout/stderr back to (1) and (2)
        os.dup2(self.save_fds[0],1)
        os.dup2(self.save_fds[1],2)
        # Close the null files
        os.close(self.null_fds[0])
        os.close(self.null_fds[1])



if ("__main__" == __name__) :
   
    parser = OptionParser( usage = "Usage: %prog [options] <structure-file-dir>", version = "%prog v0.0" )
    parser.add_option("-t", "--time", default = 20 , help = " Set the maximum time to perform the mcs search between pair of molecules")
    
    #A tuple of options and arguments passed by the user
    (opt, args) = parser.parse_args()


    mola = Chem.MolFromMol2File('mol2_file/18108.mol2', sanitize=False, removeHs=False)
    molb = Chem.MolFromMol2File('mol2_file/18110.mol2', sanitize=False, removeHs=False)
    
    MC = MCS(mola,molb,opt)

    #print MC.getMap()

    MC.draw_mcs()
    
    mcsr = MC.mcsr()
    mncar =  MC.mncar()
    ecr =  MC.ecr()
    strict = MC.tmcsr(strict_flag=True)
    loose = MC.tmcsr(strict_flag=False)

    print 'TMCRS STRICT = %f , TMCRS LOOSE = %f' % (strict, loose)
    print 'MCSR = ', mcsr
    print 'MNCAR = ', mncar
    print 'ECR = ', ecr
    
    tmp = mcsr * mncar * ecr
    
    print 'Total Strict = %f , Total Loose = %f' % (tmp * strict, tmp * loose)  

    



