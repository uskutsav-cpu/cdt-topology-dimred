// Research driver. Monte Carlo move implementations are the pinned upstream
// source with the equation-level corrections documented in DECISIONS.md.
#include "universe.hpp"
#include "simulation.hpp"
#include <fstream>
#include <iomanip>
#include <chrono>
#include <stdexcept>
#include <set>
#include <map>

void validate() {
    std::set<std::array<int,2>> edges;
    std::map<std::array<int,3>,int> faces;
    std::set<std::array<int,4>> tets;
    for (auto t: Universe::tetrasAll) {
        std::array<int,4> vs;
        for(int a=0;a<4;a++) vs[a]=t->vs[a];
        auto sorted=vs; std::sort(sorted.begin(),sorted.end());
        if(!tets.insert(sorted).second) throw std::runtime_error("duplicate tetrahedron");
        for(int a=0;a<4;a++) {
            std::array<int,3> f; int k=0;
            for(int b=0;b<4;b++) if(a!=b) f[k++]=vs[b];
            std::sort(f.begin(),f.end()); faces[f]++;
            auto n=t->tnbr[a];
            if(!Universe::tetrasAll.contains(n) || !n->neighborsTetra(t)) throw std::runtime_error("neighbor symmetry");
            for(int v:f) if(!n->hasVertex(v)) throw std::runtime_error("opposite face");
            for(int b=a+1;b<4;b++) {
                std::array<int,2> e={vs[a],vs[b]}; std::sort(e.begin(),e.end()); edges.insert(e);
            }
        }
    }
    for(auto f:faces) if(f.second!=2) throw std::runtime_error("face incidence");
    long chi=(long)Universe::verticesAll.size()-(long)edges.size()+(long)faces.size()-Universe::tetrasAll.size();
    if(chi!=0) throw std::runtime_error("Euler characteristic");
    Universe::check();
}

int main(int argc,char** argv) {
    if(argc!=12) { std::cerr<<"input output_dir seed k0 k3 target tune burn samples attempts_per_sweep check_every_move\n"; return 2; }
    std::string input=argv[1], out=argv[2];
    unsigned seed=std::stoul(argv[3]); double k0=std::stod(argv[4]),k3=std::stod(argv[5]);
    int target=std::stoi(argv[6]),tune=std::stoi(argv[7]),burn=std::stoi(argv[8]),samples=std::stoi(argv[9]),attempts=std::stoi(argv[10]);
    bool debug=std::stoi(argv[11]);
    if(target<=0 || tune<0 || burn<0 || samples<0 || attempts<=0) return 2;
    if(!Universe::initialize(input,"research",3,1)) return 3;
    Simulation::k0=k0; Simulation::k3=k3; Simulation::targetVolume=target;
    Simulation::target2Volume=0; Simulation::moveFreqs={1,1,1};
    Simulation::seed_rng(seed); Universe::seed_rng(seed^0x9e3779b9U);
    validate();
    std::ofstream log(out+"/diagnostics.csv");
    log<<"sweep,phase,N0,N3,N31,k3,peak_slice,seconds";
    for(int j=1;j<=5;j++) log<<",attempt_"<<j<<",accept_"<<j;
    log<<"\n";
    auto start=std::chrono::steady_clock::now();
    for(int i=0;i<tune+burn+samples;i++) {
        long proposed[6]={},accepted[6]={};
        for(int j=0;j<attempts;j++) {
            int m=Simulation::attemptMove(); proposed[abs(m)]++; if(m>0) accepted[m]++;
            if(debug && m>0) validate();
        }
        std::string phase=i<tune?"tune":i<tune+burn?"burn":"measure";
        double seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
        log<<std::setprecision(17)<<i+1<<","<<phase<<","<<Universe::verticesAll.size()<<","<<Universe::tetrasAll.size()<<","<<Universe::tetras31.size()<<","<<Simulation::k3<<","<<*std::max_element(Universe::sliceSizes.begin(),Universe::sliceSizes.end())<<","<<seconds;
        for(int j=1;j<=5;j++) log<<","<<proposed[j]<<","<<accepted[j];
        log<<"\n"; log.flush();
        if(i<tune) Simulation::tune_once();
        if(i>=tune+burn) {
            validate();
            std::string path=out+"/geometry_"+std::to_string(i-tune-burn)+".dat";
            if(std::ifstream(path).good()) throw std::runtime_error("raw output already exists");
            Universe::exportGeometry(path);
        }
    }
    return 0;
}
