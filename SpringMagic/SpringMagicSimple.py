import copy
import os
import math
import pymel.core as pm
import pymel.core.datatypes as dt
import maya.mel as mm


versionList=['v',0.4,2017,17,1,'SpringMagicOnly']
version= ".".join([str(o) for o in versionList])
#################### Global Variable
sceneUnit= pm.currentUnit(l=True,q=True)
#################### UI Function Assign
#################### UI definition

#################### Function Definition
######## Misc Function
def InteractivePlayback():
    pm.setCurrentTime(pm.playbackOptions(q=True,minTime=True))
    mm.eval('InteractivePlayback;')
    pm.setCurrentTime(pm.playbackOptions(q=True,minTime=True))

def clearAnim():
    clearKeys((startFrame,endFrame))
    pm.currentTime(startFrame,edit=True)

def getTimeRange(*arg):
    if not getSpringAttr('SpringTimeRange'):
        setSpringAttr('SpringStart',int(pm.playbackOptions(q=True,minTime=True)))
        setSpringAttr('SpringEnd',int(pm.playbackOptions(q=True,maxTime=True)))
        return (getSpringAttr('SpringStart'),getSpringAttr('SpringEnd'))
    else:
        return (getSpringAttr('SpringStart'),getSpringAttr('SpringEnd'))

def alignOb(alignOb,ob):
    alignObMatrix = pm.xform(alignOb,ws=True,q=True,m=True)
    pm.xform(ob,m=alignObMatrix)

def constraintOb(ob,tar):
    pm.pointConstraint(ob,tar)
    pm.orientConstraint(ob,tar)

def getTranslate(ob):
    tr = tuple(pm.xform(ob,ws=True,q=True,rp=True))
    return tr

def clearKeys(sfef):
    pm.cutKey(time=sfef)

######## Classic Spring Magic
def springPasteBonePose():
    print type(springUpAxis_comboBox.getSelect())

def springBindPose():
    pm.runtime.GoToBindPose()

def springStraightBonePose(bone):
    boneChain = getBoneChain(bone)
    if boneChain:
        for bone in boneChain[:-1]:
            bone.setRotation([0,0,0])
            bone.setAttr('rotateAxis', [0,0,0])
            bone.setAttr('jointOrient', [0,0,0])

def createEndJoint(bone):
    if bone.getParent():
        jointRoot=bone.getParent()
        poList=[]
        for j in [bone,jointRoot]:
            poList.append(dt.Vector(pm.xform(j,q=True,ws=True,t=True)))
        endJointPos=(poList[0]-poList[1])*2+poList[0]
        pm.select(bone,r=True)
        endJoint=pm.joint(p=endJointPos)
        pm.joint(bone,e=True,zso=True,oj='xyz')
        return endJoint

def createBoneFromSelection():
    bonObs =[]
    selection = pm.selected()
    if not selection:
        return
    obRoot = selection[0].getParent()
    pm.select(obRoot)
    index = 0
    while index<len(selection):
        ob=selection[index]
        bone = pm.joint(p=getTranslate(ob))
        bonObs.append((bone,ob))
        #constraintOb(bonObs[index][0],bonObs[index][1])
        index+=1
    #obRoot = pm.listRelatives(bonObs[0][1],p=True)
    endJoint=createEndJoint(bonObs[len(bonObs)-1][0])
    for obs in bonObs:
        pm.orientConstraint(obs[0],obs[1],mo=True)
        pm.pointConstraint(obs[0],obs[1],mo=True)
    bonObs.append((endJoint,None))
    return bonObs

def createBone(Ob):
    pm.select(Ob,r=True)
    bonObs =[]
    obRoot = pm.listRelatives(Ob,p=True)
    obChain = getBoneChain(Ob)
    for s in obChain:
        index = obChain.index(s)
        bone =pm.joint(p=getTranslate(s))
        bonObs.append((pm.ls(bone)[0],s))
        if index==0:
            pm.parent(bone,obRoot)
        else:
            pm.joint(str(bonObs[index-1][0]),e=True,zso=True,oj='xyz')
        #pm.orientConstraint(bone,s,mo=True)
    endJoint=createEndJoint(bonObs[len(bonObs)-1][0])
    for obs in bonObs:
        pm.orientConstraint(obs[0],obs[1],mo=True)
    bonObs.append((endJoint,None))
    return bonObs
def getBoneChain(bone):
    # only apply on child bone, bacause need a parent bone move to cause the overlapping
    if not bone.getParent():
        return False

    # get bone chain, only get one stream, will not process branches
    boneChain = []
    boneChain.append( bone )
    childList = pm.listRelatives(bone,ad=1,typ='transform')
    childList.reverse()
    boneChain.extend(childList)
    return boneChain

def springApply(pickedBone, pickedBones,springLoop=False,springRotateRate=0.3,springTwist=0.3):
    '''
    Get idea from max scripts 'SpringMagic' made by Sichuang Yuan, but make it more friendly with Maya
    '''

    # since maya 2016, there is a new animation evaluation mode called "Parallel" which supose to improve
    # the runtime performance of maya, but the new function seems cause some problem when calculate spring magic.
    # so I'll revert evaluation mode back to old way during calculation and set it back after
    # store evaluationManager mode for 2016 or newer
    if pm.versions.current() > 201600:
        currentMode = pm.evaluationManager( q=1, mode = 1 )[0]
        pm.evaluationManager( mode = 'off' )
    # Check Unit
    if sceneUnit!='cm':
        pm.currentUnit(l='cm')
    # get pickedBone chain, only get one stream, will not process branches
    if pm.nodeType(pickedBone)=='joint':
        boneChain = getBoneChain(pickedBone)
    else:
        boneObs = createBone(pickedBone)
        boneChain=[b[0] for b in boneObs]
        pm.hide(boneChain)
    if not boneChain:
        return
    boneRoot = boneChain[0].getParent()
    # get frame range
    pm.currentTime( getTimeRange()[0], edit=True )

    # get pickedBone chain start pose and key it
    boneStartRotation = {}
    # boneStartMatirx = {}
    for bone in boneChain:
        # reset bone rotate axis as 0
        bone.setRotation = bone.getAttr('rotateAxis')
        pm.xform(bone, ra = [0,0,0])
        # get bone start rotation pose
        boneStartRotation[bone] = bone.getRotation()
        # boneStartMatirx[bone] = bone.getAttr('matrix')

        if not springLoop:
            pm.setKeyframe(bone, attribute = 'rotate')
        # delete key not at start frame
        pm.cutKey( bone, time=(getTimeRange()[0] + 1,getTimeRange()[1]) )

    # get bone start world translation
    boneWorldTranlation = {}
    previousBoneWorldTranlation = {}
    previousBoneWorldRotation = {}
    previousBoneRotateAxis = None

    loopCount = float(springLoop)
    pickedBoneCount = float(len(pickedBones))
    boneChainCount = float(len(boneChain))
    frameCount = float(getTimeRange()[1]-getTimeRange()[0])
    # caculate part
    for loop in range( int(loopCount+1) ):

        for frame in range( getTimeRange()[0], getTimeRange()[1]+1 ):

            pm.currentTime( frame, edit=True )

            for bone in boneChain:

                # get bone world translation & matrix
                boneWorldTranlation[bone] = dt.Vector( pm.xform(bone, worldSpace = 1, translation = 1, query = 1) )
                # skip caculate at first frame
                if previousBoneWorldTranlation:
                    # skip end bone
                    if not bone == boneChain[-1]:
                        # get child bone name for caculate
                        childBone = boneChain[boneChain.index(bone) + 1]

                        # get the vector from current position to previous child position
                        boneAimVector = (boneWorldTranlation[bone] - previousBoneWorldTranlation[childBone]).normal()

                        # restore current bone rotation
                        boneCurrentRotation = bone.getRotation()

                        # reset bone to start pose
                        bone.setAttr('rotate', boneStartRotation[bone])

                        childBoneHight = pm.xform( childBone, worldSpace = 1, translation = 1, query = 1 )
                        
                        # get the vector of stance pose
                        stanceTranslation = ( childBone.getAttr('matrix') * childBone.getAttr('parentMatrix') ).translate
                        
                        boneStanceVetor = (boneWorldTranlation[bone] - stanceTranslation).normal()

                        # get rotation axis and degrees bewteen two vectors
                        boneRotateDegrees = math.degrees( boneStanceVetor.angle( boneAimVector ) )
                        boneRotateAxis = boneStanceVetor.axis( boneAimVector )

                        # if the rotate axis fliped
                        if previousBoneRotateAxis:
                            if abs(math.degrees( previousBoneRotateAxis.angle( boneRotateAxis ))) > 90: 
                                # then flip it back
                                boneRotateAxis = -boneRotateAxis
                                boneRotateDegrees = -boneRotateDegrees

                        previousBoneRotateAxis = boneRotateAxis

                        # set rotate rate
                        rotateRate = 1-float(springRotateRate)

                        upVector = dt.Vector(0,1,0)
                        rotateValue = upVector * (boneRotateDegrees*rotateRate)
                        # skip rotate bone if very close to start pose
                        if abs(boneRotateDegrees) > 0.001:

                            # match up bone and stance vector with aim constraint
                            lct = pm.spaceLocator()
                            lct.setTranslation( stanceTranslation )
                            cns = pm.aimConstraint( lct, bone, aimVector = [1,0,0], upVector = upVector, worldUpVector = boneRotateAxis )
                            # keep aim result before remove constraint
                            pm.setKeyframe(bone, attribute = 'rotate')
                            pm.delete( cns, lct )
                            # do rotate bone
                            pm.rotate(bone, rotateValue, objectSpace = 1, relative = 1)

                        else:
                            # use previous frame rotation
                            bone.setAttr('rotate', boneCurrentRotation)
                            pm.setKeyframe(bone, attribute = 'rotate')






                        # apply twist
                        twist = float(springTwist)
                        if 1 > twist:
                            # reset rotat x
                            bone.setAttr('rotateX', boneStartRotation[bone][0] )
                            # creat locator with stance rotation, slow step setMatrix, need optmaize
                            lct = pm.spaceLocator()
                            lct.setRotation(pm.xform(bone,q=1,worldSpace=1,rotation=1))
                            lct_p = pm.spaceLocator()
                            lct_p.setRotation(previousBoneWorldRotation[bone])
                            # get twist delay value
                            # creat orient constraint
                            cns_X = pm.orientConstraint( lct, lct_p, bone, skip = ['y','z'] )

                            # apply twist value to constraint
                            cns_X.setAttr(lct+'W0', twist)
                            cns_X.setAttr(lct_p+'W1', 1-twist)
                            # set rotate interp as shortest
                            cns_X.setAttr('interpType', 2)

                            # get caculated x
                            boneRotateX = bone.getAttr('rotateX')
                            # apply new rotate x
                            bone.setAttr('rotateX', boneRotateX)
                            pm.setKeyframe(bone, attribute = 'rotate')

                            pm.delete( cns_X, lct, lct_p )

                # save for next frame use
                previousBoneWorldRotation[bone] = pm.xform(bone,q=1,worldSpace=1,rotation=1)
                # print previousBoneWorldRotation[bone]
                #runProgressBar( main_progressBar, 1/(loopCount+1)*(1/pickedBoneCount)*(1/boneChainCount)*(1/(frameCount+1))*100 )
            # save for next frame use
            previousBoneWorldTranlation = copy.copy(boneWorldTranlation)
    if pm.nodeType(pickedBone)!='joint':
        for o in boneObs:
            if o[1]:
                pm.bakeResults(o[1],at=['rotate'], t=getTimeRange())
        pm.delete(boneChain)
    #return Unit
    pm.currentUnit(l=sceneUnit)
    # revert evaluationManager mode for 2016 or newer
    if pm.versions.current() > 201600:
        pm.evaluationManager( mode = currentMode )
def springIt(simplify = False):
    if pm.ls(sl=1, type='joint'):
        pickedBones = pm.ls(sl=1, type='joint')
    elif pm.ls(sl=1):
        pickedBones = pm.ls(sl=1)
    else:
        return False
    ### Execution
    #playOp = pm.playbackOptions(q=True,loop=True)
    #pm.playbackOptions(loop='once')
    pm.currentTime(getTimeRange()[0],e=True)
    for bone in pickedBones:
        springApply(bone,pickedBones,springLoop=getSpringAttr('SpringLoop'),springRotateRate=getSpringAttr('SpringValue'),springTwist=getSpringAttr('SpringTwist'))
        if simplify:
            pm.filterCurve(getBoneChain(bone),f='simplify',startTime=getTimeRange()[0],endTime=getTimeRange()[1],tto=getSpringAttr('SpringReduceTolerance'))
############ UI Function
def setSpringOptionVars(unset=False):
    global SpringVarDict
    SpringVarDict = {
        'SpringValue':0.3,
        'SpringTwist':0.3,
        'SpringLoop':0,
        'SpringReduceTolerance':0.2,
        'SpringTimeRange':0,
        'SpringStart':int(pm.playbackOptions(q=True,minTime=True)),
        'SpringEnd':int(pm.playbackOptions(q=True,maxTime=True))
        }
    if unset:
        for k in SpringVarDict:
            SpringVarDict.pop[k]

def getSpringAttr(attr):
    if SpringVarDict.has_key(attr):
        SpringVarDict[attr]

def setSpringAttr(attr,val):
    if SpringVarDict.has_key(attr):
        SpringVarDict[attr]=val

def removeUI():
    pm.deleteUI('makeSpringWin')


def makeSpringUI():
    global springButtonID
    global dynHairMagicFrameID
    global dynSpringMagicFrameID
    global dynHairMagicRadioID
    global dynSpringMagicRadioID
    #global progressControlID
    if pm.window('makeSpringWin',ex=True):
        pm.deleteUI('makeSpringWin',window=True)
        pm.windowPref('makeSpringWin',remove=True)
    setSpringOptionVars()
    pm.window('makeSpringWin',menuBar=True,t="Spring Magic Maya %s" % version)
    pm.menu(tearOff=False,l="Edit")
    #start menu
    pm.menuItem(l="Reset Settings",ann="Reset all",c=lambda *arg:makeSpringUI())
    #end menu
    pm.scrollLayout('scrollLayout')
    # start scrollLayout
    pm.frameLayout(lv=False)
    ## start frameLayout
    pm.columnLayout(adjustableColumn=1)
    ### start CollumnLayout
    pm.rowColumnLayout(numberOfColumns=6,columnWidth=[(1,90),(2,60),(3,55),(4,45),(5,30),(6,45)],bgc=(0.5,0.5,0.5))
    #### start rowCollumn 6
    pm.text(label="Key Range: ")
    dynkeyRangeID = pm.radioCollection("KeyRangeRadioCollection")
    dynTimeRadioID1=pm.radioButton(label="Active",onc=lambda *arg:setSpringAttr('SpringTimeRange',0))
    dynTimeRadioID2=pm.radioButton(label="From: ",onc=lambda *arg:setSpringAttr('SpringTimeRange',1))
    pm.intField(value=getTimeRange()[0],cc=lambda *arg:setSpringAttr('SpringStart', *arg))
    pm.text(label="To: ")
    pm.intField(value=getTimeRange()[1],cc=lambda *arg:setSpringAttr('SpringEnd', *arg))
    pm.setParent('..')
    #### end rowCollumn 6
    pm.separator(style='out')
    pm.setParent('..')
    ## end frameLayout
    dynSpringMagicFrameID=pm.frameLayout(label='Spring Magic')
    #start Spring Magic Frame
    pm.rowColumnLayout(numberOfColumns=6,columnWidth=[(1,90),(2,60),(3,55),(4,45),(5,30),(6,45)])
    #start rowCollumn
    pm.text(label="Spring : ",align='right')
    pm.floatField(minValue=0, maxValue=1, value=0.3,editable=True,cc=lambda *arg:setSpringAttr('SpringValue', *arg))
    pm.text(label="Twist : ",align='right')
    pm.floatField(minValue=0, maxValue=1, value=0.3,editable=True,cc=lambda *arg:setSpringAttr('SpringTwist', *arg))
    pm.text(label="",align='right')
    pm.checkBox(label="Loop",cc=lambda *arg:setSpringAttr('SpringLoop', *arg))
    pm.setParent('..')
    #end rowCollumn
    pm.setParent('..')
    #end Spring Magic Frame
    pm.separator(style='in')
    pm.rowColumnLayout(numberOfColumns=4,columnWidth=[(1,112-30),(2,30),(3,112),(4,112)])
    springButtonID= pm.button(label="Do Simplify",c=lambda *arg:springIt(simplify=True))
    pm.floatField(minValue=0, maxValue=1, value=0.5,step=0.1,pre=2,cc=lambda *arg:setSpringAttr('SpringReduceTolerance', *arg))
    pm.button(label= "Apply",c=lambda *arg:springIt())
    pm.button(label= "Clear",c='clearAnim()')
    pm.setParent('..')
    pm.radioCollection(dynkeyRangeID,edit=True,select = pm.radioCollection(dynkeyRangeID,q=True,cia=True)[getSpringAttr('SpringTimeRange')])
    #pm.radioCollection(dynJointFalloffID,edit=True,select = pm.radioCollection(dynJointFalloffID,q=True,cia=True)[getSpringAttr('SpringHairFalloff')])
    #pm.radioCollection(dynPickMethodID,edit=True,select = dynHierachyRadioID if getSpringAttr('SpringPickType') else dynSelectionRadioID)
    #pm.radioCollection(dynSpringMethodID,edit=True,select = dynHairMagicRadioID if getSpringAttr('SpringMethod') else dynSpringMagicRadioID)
    #progressControlID=pm.text(label="...",bgc=(0,.5,0.15),fn='boldLabelFont',h=20)
    pm.showWindow()
# Script job
#sJob_main_updateUI = pm.scriptJob( event= ["SceneOpened", deleteSpringOptionVars], protected = True )